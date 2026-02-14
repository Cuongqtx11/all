# Bot Kích Hoạt Locket Gold

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://core.telegram.org/bots)

**Bot Telegram tự động kích hoạt Locket Gold.**
*Đã được tối ưu hoá bởi admin s2codeteam.*

</div>

---

## Hướng dẫn cài đặt trên Replit

1. Tải file ZIP về máy, giải nén ra
2. Tạo Replit mới (chọn ngôn ngữ Python), kéo thả **tất cả file bên trong** vào thư mục gốc
3. Mở file `.env.example`, điền đầy đủ `BOT_TOKEN`, `NEXTDNS_KEY`, `ADMIN_ID`
4. Mở cửa sổ Shell, dán lệnh sau:

```bash
pip install python-telegram-bot aiohttp requests python-dotenv && python main.py
```

5. Bot sẽ tự nhắn cho admin yêu cầu gửi file `api.txt` -> gửi file vào là hoạt động

> **Lưu ý:** Nếu file nằm trong thư mục con (ví dụ `Locket-Gold-2`), chạy lệnh sau:
> ```bash
> cd Locket-Gold-2 && pip install python-telegram-bot aiohttp requests python-dotenv && python main.py
> ```

> **Quan trọng:** Chỉ được chạy **1 bot duy nhất** với cùng 1 BOT_TOKEN. Nếu đang chạy ở Replit khác, tắt nó trước rồi mới chạy ở đây.

---

## Cấu hình `.env.example`

```env
BOT_TOKEN=
NEXTDNS_KEY=
ADMIN_ID=
```

| Giá trị | Lấy ở đâu |
| :--- | :--- |
| **BOT_TOKEN** | [@BotFather](https://t.me/BotFather) trên Telegram |
| **NEXTDNS_KEY** | [NextDNS](https://my.nextdns.io/account) > Tài khoản > API |
| **ADMIN_ID** | Gửi `/start` cho [@userinfobot](https://t.me/userinfobot) |

---

## Các lệnh Bot

### Người dùng

| Lệnh | Mô tả |
| :--- | :--- |
| `/start` | Menu chính |
| `/setlang` | Đổi ngôn ngữ (VI / EN) |
| `/help` | Hướng dẫn sử dụng |

### Quản trị viên

| Lệnh | Mô tả |
| :--- | :--- |
| `/stats` | Xem thống kê hệ thống |
| `/noti <nội dung>` | Gửi thông báo đến tất cả người dùng |
| `/rs <user_id>` | Đặt lại lượt dùng cho người dùng |
| `/setdonate` | Trả lời vào ảnh để đặt ảnh donate |
| `/settoken` | Xem hướng dẫn gửi token |
| **Gửi file `.txt` / `.json`** | Bot tự đọc token và lưu vào hệ thống |

---

## Lưu ý

> **Dự án này chỉ dành cho mục đích GIÁO DỤC và NGHIÊN CỨU.**

---

<div align="center">

Được tạo bởi [Thanh Do](https://github.com/thanhdo1110)

</div>
