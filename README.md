# 🤖 AI-Powered Personal Finance Bot

> Một trợ lý tài chính thông minh trên Telegram, giúp bạn ghi chép thu chi hàng ngày bằng ngôn ngữ tự nhiên và tự động xuất báo cáo trực quan.

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Telegram API](https://img.shields.io/badge/Telegram_Bot-API-2CA5E0.svg)](https://core.telegram.org/bots)
[![Gemini API](https://img.shields.io/badge/AI-Google_Gemini-orange.svg)](https://ai.google.dev/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-336791.svg)](https://www.postgresql.org/)

---

## 🌟 Live Demo
💬 **Chat với Bot ngay tại đây:** [@tinppb_finance_bot](https://t.me/tinppb_finance_bot)

*(Ảnh minh họa tính năng bóc tách NLP & thống kê)*
<p align="center">
  <img src="demo.PNG" alt="Demo Chat NLP" width="350">
</p>

---

## ✨ Tính năng nổi bật (Features)

*   🧠 **Ghi chép bằng Ngôn ngữ Tự nhiên (NLP):** Không cần cú pháp phức tạp, chỉ cần nhắn *"Sáng ăn bún bò 45k, đổ xăng 50k"*. Bot sử dụng LLM (Google Gemini) để phân tích, bóc tách thực thể và phân loại danh mục tự động.
*   🛡️ **Trích xuất Dữ liệu An toàn (Fault-Tolerant):** Tích hợp luồng xử lý lỗi thông minh (Retry mechanisms) và Regex Fallbacks, đảm bảo dữ liệu JSON trả về từ AI luôn chuẩn xác và không bị crash hệ thống.
*   📊 **Báo cáo Trực quan (Data Visualization):** Tự động tổng hợp và vẽ biểu đồ (Bar Chart, Pie Chart) ngay trong bộ nhớ (In-memory) bằng Matplotlib và gửi thẳng qua Telegram mà không cần lưu trữ file thừa.
*   📅 **Thống kê linh hoạt:** Theo dõi chi tiêu theo bất kỳ tháng/năm nào, có biểu đồ so sánh xu hướng thu chi trong suốt cả năm (lệnh `/tonghop`).
*   ⚡ **Database Tối ưu hóa:** Xây dựng trên PostgreSQL với SQLAlchemy ORM, thiết lập Connection Pooling vững chắc, tự động "ping" giữ kết nối trên môi trường Cloud.

---

## 🛠️ Công nghệ sử dụng (Tech Stack)

*   **Ngôn ngữ:** Python 3.10+
*   **AI/LLM:** Google GenAI SDK (Gemini 3.1 Flash Lite)
*   **Database:** PostgreSQL, SQLAlchemy (ORM)
*   **Thư viện Data/Biểu đồ:** Matplotlib, Numpy
*   **Bot Framework:** Python-Telegram-Bot
*   **Deployment:** Render Cloud (Kèm Flask Server để Keep-Alive)

---

## 🚀 Hướng dẫn Cài đặt (Local Setup)

Nếu bạn muốn tự chạy bot trên máy cá nhân, hãy làm theo các bước sau:

**1. Clone dự án**
```bash
git clone https://github.com/tinppb/tin-finance-bot.git
cd tin-finance-bot
```

**2. Tạo môi trường ảo (Khuyên dùng) và cài đặt thư viện**
```bash
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

pip install -r requirements.txt
```

**3. Cấu hình biến môi trường**
Tạo file `.env` ở thư mục gốc và thêm các key sau:
```env
BOT_TOKEN=nhập_telegram_bot_token_cua_ban
GEMINI_API_KEY=nhập_gemini_api_key_cua_ban
DATABASE_URL=postgresql://username:password@host/database
```

**4. Khởi chạy Bot**
```bash
python main.py
```
*Lưu ý: Bảng database sẽ tự động được tạo ở lần chạy đầu tiên (nhờ `Base.metadata.create_all`).*

---

## 📜 Danh sách Lệnh (Commands)

*   `/start` - Khởi động và xem hướng dẫn
*   `/thongke [tháng] [năm]` - Báo cáo thu chi (VD: `/thongke 10 2026`)
*   `/lichsu [tháng] [năm]` - Liệt kê nhật ký chi tiết
*   `/bieuedo [tháng] [năm]` - Biểu đồ thống kê Thu/Chi & Tỷ lệ danh mục
*   `/tonghop [năm]` - Biểu đồ tổng hợp cả năm (12 tháng)
*   `/undo` - Hoàn tác (xóa) giao dịch vừa nhập gần nhất

---
*Developed by [Tín Phạm](https://github.com/tinppb) - 2026*
