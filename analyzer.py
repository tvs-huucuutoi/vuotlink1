import ipaddress
import re
import socket
from urllib.parse import urlparse, urljoin, urldefrag
import requests
from bs4 import BeautifulSoup

MAX_REDIRECTS = 8
MAX_BYTES = 1_500_000
MAX_URLS = 10
TIMEOUT = (5, 12)
USER_AGENT = "LinkCodeTool/2.0 (+public-page analyzer)"
REDIRECT_CODES = {301, 302, 303, 307, 308}
CODE_PATTERNS = [
    r"(?i)\b(?:mã|ma|code|coupon|voucher|promo(?:tion)?\s*code)\s*[:：#-]\s*([A-Z0-9][A-Z0-9_-]{3,31})",
    r"(?i)\b(?:verification|access)\s*code\s*[:：#-]\s*([A-Z0-9][A-Z0-9_-]{3,31})",
]

def _public_addresses(host, port):
    try:
        ip = ipaddress.ip_address(host)
        addresses = [ip]
    except ValueError:
        try:
            infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except socket.gaierror:
            raise ValueError("Không phân giải được tên miền.")
        addresses = list({ipaddress.ip_address(info[4][0]) for info in infos})
    if not addresses or any(not ip.is_global for ip in addresses):
        raise ValueError("Từ chối địa chỉ không công khai hoặc mạng nội bộ.")
    return addresses

def validate_public_url(url):
    if not isinstance(url, str) or len(url) > 2048:
        raise ValueError("URL không hợp lệ hoặc quá dài.")
    url = url.strip()
    if not url:
        raise ValueError("Vui lòng nhập URL.")
    if "://" not in url:
        url = "https://" + url
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError:
        raise ValueError("URL hoặc cổng kết nối không hợp lệ.")
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError("Chỉ hỗ trợ URL HTTP/HTTPS.")
    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Tên miền không hợp lệ hoặc URL chứa thông tin đăng nhập.")
    host = parsed.hostname.rstrip(".").lower()
    if not host or host in {"localhost", "localhost.localdomain"}:
        raise ValueError("Không hỗ trợ localhost.")
    port = port or (443 if parsed.scheme.lower() == "https" else 80)
    _public_addresses(host, port)
    # Chỉ cho phép cổng web phổ biến.
    if port not in (80, 443, 8080, 8443):
        raise ValueError("Chỉ hỗ trợ cổng web 80, 443, 8080 hoặc 8443.")
    return urldefrag(parsed._replace(scheme=parsed.scheme.lower()).geturl())[0]

def _extract(text):
    found = []
    for pattern in CODE_PATTERNS:
        for code in re.findall(pattern, text):
            if code not in found:
                found.append(code)
    return found[:100]

def analyze_text(text, source_url=""):
    soup = BeautifulSoup(text, "html.parser")
    clean_text = soup.get_text(" ", strip=True) if ("<" in text and ">" in text) else text
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    meta = soup.find("meta", attrs={"name": re.compile("^description$", re.I)}) if soup else None
    description = meta.get("content", "").strip() if meta else ""
    codes = _extract(clean_text)
    return {
        "input_url": source_url or "(nội dung dán thủ công)",
        "final_url": source_url or "",
        "status": None,
        "content_type": "text/plain",
        "redirects": [],
        "title": title[:300] or "(Nội dung đã dán)",
        "description": description[:500],
        "codes": codes,
        "links": [],
        "text_preview": clean_text[:2000],
    }

def analyze_url(raw_url):
    current = validate_public_url(raw_url)
    redirects = []
    session = requests.Session()
    session.trust_env = False
    try:
        for hop in range(MAX_REDIRECTS + 1):
            current = validate_public_url(current)
            # Kiểm tra DNS ngay trước mỗi request. Requests vẫn tự phân giải ở tầng socket;
            # môi trường production nên đặt thêm egress firewall chặn mạng private.
            parsed = urlparse(current)
            _public_addresses(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
            with session.get(
                current,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain,application/xhtml+xml;q=0.9"},
                timeout=TIMEOUT, allow_redirects=False, stream=True
            ) as response:
                if response.status_code in REDIRECT_CODES and response.headers.get("Location"):
                    destination = urljoin(current, response.headers["Location"])
                    if hop >= MAX_REDIRECTS:
                        raise ValueError("Đã vượt quá giới hạn 8 lần chuyển hướng.")
                    redirects.append({"status": response.status_code, "url": current, "destination": destination})
                    current = destination
                    continue
                content_type = response.headers.get("Content-Type", "")
                if not any(x in content_type.lower() for x in ("text/html", "text/plain", "application/xhtml")):
                    raise ValueError("Trang đích không trả về HTML hoặc văn bản có thể phân tích.")
                chunks, total = [], 0
                for chunk in response.iter_content(16384):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise ValueError("Nội dung trang vượt quá giới hạn 1,5 MB.")
                    chunks.append(chunk)
                encoding = response.encoding or "utf-8"
                body = b"".join(chunks).decode(encoding, errors="replace")
                final_url = response.url
                status = response.status_code
                break
        else:
            raise ValueError("Không thể hoàn tất chuyển hướng.")
    finally:
        session.close()

    soup = BeautifulSoup(body, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else "(Không có tiêu đề)"
    desc_tag = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    description = desc_tag.get("content", "").strip() if desc_tag else ""
    page_text = soup.get_text(" ", strip=True)
    links = []
    for tag in soup.find_all("a", href=True)[:100]:
        href = urljoin(final_url, tag["href"].strip())
        if href.startswith(("http://", "https://")):
            item = {"label": tag.get_text(" ", strip=True)[:100] or "(không có nhãn)", "url": href[:2048]}
            if item not in links:
                links.append(item)
    return {
        "input_url": str(raw_url)[:2048],
        "final_url": final_url,
        "status": status,
        "content_type": content_type[:200],
        "redirects": redirects,
        "title": title[:300],
        "description": description[:500],
        "codes": _extract(page_text),
        "links": links[:50],
        "text_preview": page_text[:2000],
    }
