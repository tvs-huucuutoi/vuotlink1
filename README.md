# LinkCode Tool V2

Ứng dụng Flask phân tích tối đa 10 URL công khai/lần, theo dõi redirect HTTP thông thường, trích xuất mã được gắn nhãn trong HTML/văn bản, hỗ trợ dán nội dung thủ công, lưu lịch sử SQLite, tìm kiếm/xóa và xuất CSV.

## Chạy local (Windows)
```powershell
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
py app.py
```
Mở http://127.0.0.1:5000

## Triển khai Render
- Tạo Web Service từ repository GitHub.
- Build: `pip install -r requirements.txt`
- Start: `gunicorn app:app --workers 2 --threads 4 --timeout 45`
- Health check: `/health`
- Cấu hình mặc định dùng `DB_PATH=/tmp/linkcode_tool.sqlite3`; trên Render Free dữ liệu có thể mất khi khởi động lại/redeploy/instance thay đổi.
- Muốn giữ lịch sử lâu dài: dùng gói Render hỗ trợ Persistent Disk, tạo disk mount tại `/var/data`, rồi đổi biến môi trường `DB_PATH=/var/data/linkcode_tool.sqlite3`. Không cần thay đổi mã nguồn.

## Tính năng
- Chế độ tự động: tối đa 10 URL/lần, redirect tối đa 8 bước, giới hạn nội dung 1,5 MB.
- Chế độ hỗ trợ trình duyệt: mở link ở tab mới; người dùng tự thao tác rồi dán URL cuối hoặc nội dung công khai vào ô phân tích thủ công.
- SQLite history, tìm kiếm, xóa từng mục/xóa tất cả, tải CSV.
- Giao diện tiếng Việt responsive.

## Giới hạn an toàn
Chỉ đọc nội dung HTTP/HTTPS công khai. Không vượt CAPTCHA, đăng nhập, paywall, nhiệm vụ quảng cáo hoặc xác minh; không đọc cookie/session của tab khác; không chạy JavaScript của trang. Trình duyệt không cho website này tự đọc tab khác nếu không có tiện ích mở rộng được cài đặt và cấp quyền.
Không đưa URL chứa token riêng tư hoặc thông tin nhạy cảm vào công cụ. Đây là ứng dụng mẫu; khi mở công khai nên dùng egress firewall ở hạ tầng để chặn mạng nội bộ/metadata IP và cân nhắc xác thực người dùng, CAPTCHA chống lạm dụng và giới hạn tốc độ nâng cao.
