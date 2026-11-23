# LinkCode Tool – Web Edition

## Yêu cầu
- Python 3.10 trở lên
- Kết nối Internet để tải các thư viện và phân tích trang web công khai

## Cài đặt trên Windows
Mở CMD hoặc PowerShell tại thư mục dự án:

```powershell
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
py app.py
```

Mở trình duyệt tại:

http://127.0.0.1:5000

Dừng máy chủ bằng `Ctrl + C` trong cửa sổ terminal.

## Chức năng
- Kiểm tra URL HTTP/HTTPS công khai.
- Theo dõi tối đa 8 lần chuyển hướng.
- Đọc tối đa 1 MB HTML/văn bản.
- Trích xuất mã có nhãn rõ ràng như `Code: ABC123`, `Mã: ABC123`.
- Hiển thị tiêu đề, mô tả, URL cuối, liên kết và phần xem trước văn bản.

## Giới hạn
Tool không giải CAPTCHA, không tự hoàn thành nhiệm vụ quảng cáo/xác minh, không đọc nội dung yêu cầu đăng nhập và không chạy JavaScript của trang. Tool chỉ phân tích nội dung HTTP công khai được máy chủ trả về.

## Lưu ý triển khai
Bản mẫu chỉ bind vào `127.0.0.1`, không phải máy chủ production. Trước khi triển khai công khai cần bổ sung kiểm soát truy cập, giới hạn tần suất, bảo vệ DNS rebinding ở tầng kết nối, logging và cấu hình máy chủ phù hợp.
