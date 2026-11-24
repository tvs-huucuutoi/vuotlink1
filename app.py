import csv
import io
import os
import re
from datetime import datetime, timezone
from flask import Flask, jsonify, render_template, request, Response
from modules.analyzer import analyze_url, analyze_text, MAX_URLS
from modules.database import init_db, save_result, list_history, delete_history, get_history

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 256 * 1024
app.config["JSON_AS_ASCII"] = False
init_db()

# Giới hạn đơn giản theo IP để giảm spam trên bản triển khai công khai.
_RATE = {}
RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))

def rate_limited():
    import time
    now = time.time()
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    recent = [t for t in _RATE.get(ip, []) if now - t < 60]
    if len(recent) >= RATE_LIMIT:
        _RATE[ip] = recent
        return True
    recent.append(now)
    _RATE[ip] = recent
    return False

@app.before_request
def guard_api():
    if request.path.startswith("/api/") and rate_limited():
        return jsonify({"ok": False, "error": "Bạn thao tác quá nhanh. Vui lòng thử lại sau một phút."}), 429

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "LinkCode Tool V2"})

@app.post("/api/analyze")
def api_analyze():
    payload = request.get_json(silent=True) or {}
    urls = payload.get("urls")
    if urls is None:
        one = payload.get("url", "")
        urls = [one]
    if not isinstance(urls, list) or not 1 <= len(urls) <= MAX_URLS:
        return jsonify({"ok": False, "error": f"Vui lòng gửi từ 1 đến {MAX_URLS} URL."}), 400
    results = []
    for raw in urls:
        try:
            result = analyze_url(raw)
            save_result("url", str(raw)[:2048], result)
            results.append({"ok": True, **result})
        except (ValueError, TypeError) as exc:
            results.append({"ok": False, "input_url": str(raw)[:2048], "error": str(exc)})
        except Exception:
            app.logger.exception("URL analysis failed")
            results.append({"ok": False, "input_url": str(raw)[:2048], "error": "Không thể phân tích URL này."})
    return jsonify({"ok": True, "results": results})

@app.post("/api/analyze-text")
def api_analyze_text():
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "")
    source_url = payload.get("source_url", "")
    if not isinstance(text, str) or not text.strip():
        return jsonify({"ok": False, "error": "Hãy dán nội dung văn bản công khai để phân tích."}), 400
    if len(text) > 200_000:
        return jsonify({"ok": False, "error": "Văn bản vượt quá giới hạn 200 KB."}), 413
    result = analyze_text(text, source_url)
    save_result("text", source_url[:2048] if isinstance(source_url, str) else "", result)
    return jsonify({"ok": True, **result})

@app.get("/api/history")
def api_history():
    q = request.args.get("q", "")[:100]
    try:
        limit = max(1, min(100, int(request.args.get("limit", "50"))))
    except ValueError:
        limit = 50
    return jsonify({"ok": True, "items": list_history(q, limit)})

@app.delete("/api/history")
def api_clear_history():
    delete_history()
    return jsonify({"ok": True, "message": "Đã xóa toàn bộ lịch sử."})

@app.delete("/api/history/<int:item_id>")
def api_delete_history(item_id):
    deleted = delete_history(item_id)
    return jsonify({"ok": bool(deleted), "message": "Đã xóa mục lịch sử." if deleted else "Không tìm thấy mục này."}), (200 if deleted else 404)

@app.get("/api/export.csv")
def api_export():
    rows = get_history()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Thời gian UTC", "Loại", "Đầu vào", "URL đích", "HTTP", "Mã tìm thấy", "Tiêu đề"])
    for row in rows:
        writer.writerow([row["created_at"], row["kind"], row["input_value"], row["final_url"], row["status"], ", ".join(row["codes"]), row["title"]])
    data = "\ufeff" + output.getvalue()
    return Response(data, mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=linkcode-history.csv"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
