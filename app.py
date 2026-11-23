from flask import Flask, render_template, request, jsonify
from urllib.parse import urlparse, urljoin
import ipaddress
import re
import socket
import requests
from bs4 import BeautifulSoup

app = Flask(__link__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024  # Chỉ nhận payload URL nhỏ từ trình duyệt

MAX_REDIRECTS = 8
MAX_BYTES = 1_000_000
TIMEOUT = (5, 12)
USER_AGENT = "LinkCodeTool/1.0 (public-page analyzer)"


def validate_public_url(url: str) -> str:
    """Chỉ chấp nhận HTTP(S) tới host công khai; chặn localhost/mạng nội bộ."""
    if not isinstance(url, str) or len(url) > 2048:
        raise ValueError("URL không hợp lệ hoặc quá dài.")

    url = url.strip()
    if not url:
        raise ValueError("Vui lòng nhập URL.")

    if "://" not in url:
        url = "https://" + url

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Chỉ hỗ trợ URL http:// hoặc https://.")
    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Tên miền không hợp lệ.")

    host = parsed.hostname.rstrip(".")
    try:
        ip = ipaddress.ip_address(host)
        addresses = [ip]
    except ValueError:
        try:
            infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80),
                                       type=socket.SOCK_STREAM)
            addresses = list({ipaddress.ip_address(info[4][0]) for info in infos})
        except socket.gaierror:
            raise ValueError("Không phân giải được tên miền.")

    if not addresses or any(not ip.is_global for ip in addresses):
        raise ValueError("Từ chối địa chỉ không công khai hoặc mạng nội bộ.")

    # Chuẩn hóa URL, bỏ fragment vì fragment không được gửi lên máy chủ.
    return parsed._replace(fragment="").geturl()


def fetch_public_page(start_url: str):
    current = validate_public_url(start_url)
    redirect_chain = []
    session = requests.Session()
    session.trust_env = False  # Không dùng proxy từ biến môi trường

    try:
        for hop in range(MAX_REDIRECTS + 1):
            current = validate_public_url(current)
            response = session.get(
                current,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain;q=0.9,*/*;q=0.1"},
                timeout=TIMEOUT,
                allow_redirects=False,
                stream=True,
            )

            status = response.status_code
            location = response.headers.get("Location")

            if status in (301, 302, 303, 307, 308) and location:
                next_url = urljoin(current, location)
                response.close()
                redirect_chain.append({"status": status, "url": current, "destination": next_url})
                if hop == MAX_REDIRECTS:
                    raise ValueError("Đã vượt quá giới hạn chuyển hướng.")
                current = next_url
                continue

            content_type = response.headers.get("Content-Type", "")
            if not any(t in content_type.lower() for t in ("text/html", "text/plain", "application/xhtml")):
                response.close()
                raise ValueError("Trang đích không trả về HTML hoặc văn bản có thể phân tích.")

            chunks, total = [], 0
            for chunk in response.iter_content(chunk_size=16384):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_BYTES:
                    response.close()
                    raise ValueError("Nội dung trang vượt quá giới hạn 1 MB.")
                chunks.append(chunk)

            encoding = response.encoding or "utf-8"
            body = b"".join(chunks).decode(encoding, errors="replace")
            final_url = response.url
            response.close()

            return {
                "status": status,
                "final_url": final_url,
                "content_type": content_type,
                "html": body,
                "redirects": redirect_chain,
            }

        raise ValueError("Không thể hoàn tất chuyển hướng.")
    finally:
        session.close()


def extract_page_data(html: str, final_url: str):
    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.get_text(" ", strip=True) if soup.title else "(Không có tiêu đề)"
    description_tag = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    description = description_tag.get("content", "").strip() if description_tag else ""

    # Trích xuất mã được gắn nhãn rõ ràng trong nội dung công khai.
    text = soup.get_text(" ", strip=True)
    patterns = [
        r"(?i)\b(?:mã|ma|code|coupon|voucher|promo(?:tion)?\s*code)\s*[:：#-]\s*([A-Z0-9][A-Z0-9_-]{3,31})",
        r"(?i)\b(?:verification|access)\s*code\s*[:：#-]\s*([A-Z0-9][A-Z0-9_-]{3,31})",
    ]
    found = []
    for pattern in patterns:
        for match in re.findall(pattern, text):
            if match not in found:
                found.append(match)

    # Thu thập URL liên kết tương đối/đầy đủ để người dùng xem xét.
    links = []
    for tag in soup.find_all("a", href=True)[:100]:
        href = urljoin(final_url, tag["href"].strip())
        label = tag.get_text(" ", strip=True)[:100]
        if href.startswith(("http://", "https://")):
            item = {"label": label or "(không có nhãn)", "url": href}
            if item not in links:
                links.append(item)

    return {
        "title": title[:300],
        "description": description[:500],
        "codes": found,
        "links": links[:50],
        "text_preview": text[:1200],
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/analyze")
def analyze():
    payload = request.get_json(silent=True) or {}
    url = payload.get("url", "")
    try:
        page = fetch_public_page(url)
        data = extract_page_data(page["html"], page["final_url"])
        return jsonify({
            "ok": True,
            "input_url": url,
            "final_url": page["final_url"],
            "status": page["status"],
            "content_type": page["content_type"],
            "redirects": page["redirects"],
            **data,
        })
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except requests.RequestException:
        return jsonify({"ok": False, "error": "Không thể tải trang. Kiểm tra URL hoặc thử lại sau."}), 502
    except Exception:
        app.logger.exception("Unexpected analyzer error")
        return jsonify({"ok": False, "error": "Đã xảy ra lỗi khi phân tích trang."}), 500


if __name__ == "__main__":
    # Chỉ chạy trên máy local. Không bật debug khi sử dụng.
    app.run(host="127.0.0.1", port=5000, debug=False)
