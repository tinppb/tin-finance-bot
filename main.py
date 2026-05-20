import os
import json
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from telegram import BotCommand

# Import cấu hình Database từ file database.py
from database import SessionLocal, Transaction
# Import bộ giữ mạng sống từ file keep_alive.py
from keep_alive import keep_alive

# Load các biến môi trường (.env trên máy local hoặc Environment Variables trên Render)
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Khởi tạo Client Gemini thế hệ mới
client = genai.Client(api_key=GEMINI_API_KEY)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /start khi người dùng bắt đầu chat với bot"""
    user_name = update.message.from_user.first_name
    await update.message.reply_text(
        f"Chào {user_name}! Mình là Quản gia Tài chính AI.\n"
        "Cứ nhắn tự nhiên như: 'Sáng ăn bún bò 45k, đổ xăng 50k' hoặc 'Mới nhận lương làm thêm 3 củ'.\n\n"
        "Các lệnh có sẵn:\n"
        "📊 /thongke - Xem báo cáo thu chi tháng này\n"
        "⏪ /undo - Xóa nhanh giao dịch vừa nhập"
    )

async def thongke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /thongke tính tổng thu chi trong tháng hiện tại từ Cloud DB"""
    user_id = str(update.message.from_user.id)
    now = datetime.now()
    
    try:
        db = SessionLocal()
        # Lấy tất cả giao dịch của user này
        transactions = db.query(Transaction).filter(Transaction.user_id == user_id).all()
        db.close()
        
        tong_thu = 0
        tong_chi = 0
        chi_tiet_chi = {}
        
        # Quét qua dữ liệu để lọc theo tháng/năm hiện tại
        for t in transactions:
            if t.created_at.month == now.month and t.created_at.year == now.year:
                if t.type == 'income':
                    tong_thu += t.amount
                elif t.type == 'expense':
                    tong_chi += t.amount
                    # Cộng dồn tiền theo danh mục
                    if t.category in chi_tiet_chi:
                        chi_tiet_chi[t.category] += t.amount
                    else:
                        chi_tiet_chi[t.category] = t.amount
        
        # Định dạng tin nhắn báo cáo bằng HTML
        msg = f"📊 <b>BÁO CÁO THÁNG {now.month}/{now.year}</b>\n\n"
        msg += f"🟢 Tổng thu: <b>{tong_thu:,.0f} VNĐ</b>\n"
        msg += f"🔴 Tổng chi: <b>{tong_chi:,.0f} VNĐ</b>\n"
        msg += f"-----------------------\n"
        msg += f"<b>Chi tiết các khoản chi:</b>\n"
        
        if not chi_tiet_chi:
            msg += "<i>Chưa có khoản chi nào trong tháng này.</i>\n"
        else:
            for cat, amount in chi_tiet_chi.items():
                msg += f"  - {cat}: {amount:,.0f} VNĐ\n"
                
        msg += f"\n💰 <b>Số dư tháng này: {(tong_thu - tong_chi):,.0f} VNĐ</b>"
        
        await update.message.reply_text(msg, parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi khi lấy dữ liệu thống kê: {e}")

async def lichsu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Liệt kê TOÀN BỘ danh sách chi tiết các giao dịch trong tháng hiện tại"""
    user_id = str(update.message.from_user.id)
    now = datetime.now()
    
    try:
        db = SessionLocal()
        # Lấy tất cả lịch sử, mới nhất lên đầu
        transactions = db.query(Transaction).filter(
            Transaction.user_id == user_id
        ).order_by(Transaction.id.desc()).all()
        db.close()
        
        # Tạo một mảng để chứa các đoạn tin nhắn (tránh bị quá giới hạn của Telegram)
        messages = []
        current_msg = f"📜 <b>NHẬT KÝ CHI TIÊU THÁNG {now.month}/{now.year}</b>\n"
        current_msg += "---------------------------------\n"
        
        count = 0
        for t in transactions:
            if t.created_at.month == now.month and t.created_at.year == now.year:
                count += 1
                ngay_thang = t.created_at.strftime("%d/%m")
                icon = '🟢' if t.type == 'income' else '🔴'
                
                # Tạo nội dung cho 1 dòng
                line = f"{icon} <b>{ngay_thang}</b> - {t.category}: <b>{t.amount:,.0f}đ</b> <i>({t.note})</i>\n"
                
                # Nếu tin nhắn hiện tại sắp chạm ngưỡng 4000 ký tự của Telegram -> Cắt và sang trang mới
                if len(current_msg) + len(line) > 3800:
                    messages.append(current_msg) # Cất tin nhắn hiện tại vào mảng
                    current_msg = "" # Xóa trắng để viết tin nhắn tiếp theo
                
                current_msg += line
        
        if count == 0:
            current_msg += "<i>Chưa có giao dịch nào được ghi nhận trong tháng này.</i>"
            
        # Đưa đoạn tin nhắn cuối cùng vào mảng
        messages.append(current_msg)
        
        # Vòng lặp gửi lần lượt từng tin nhắn trong mảng cho người dùng
        for m in messages:
            if m.strip(): # Chỉ gửi nếu tin nhắn có nội dung
                await update.message.reply_text(m, parse_mode='HTML')
                
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi khi lấy nhật ký chi tiêu: {e}")

async def undo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /undo xóa giao dịch vừa nhập gần nhất của user"""
    user_id = str(update.message.from_user.id)
    
    try:
        db = SessionLocal()
        # Tìm giao dịch cuối cùng của user (ID lớn nhất)
        last_tx = db.query(Transaction).filter(Transaction.user_id == user_id).order_by(Transaction.id.desc()).first()
        
        if last_tx:
            thong_tin_xoa = f"{last_tx.category} ({last_tx.amount:,.0f} VNĐ)"
            db.delete(last_tx)
            db.commit()
            await update.message.reply_text(f"⏪ <b>Đã hoàn tác (Undo)!</b>\nĐã xóa dữ liệu: <i>{thong_tin_xoa}</i>", parse_mode='HTML')
        else:
            await update.message.reply_text("❌ Bạn chưa có giao dịch nào gần đây để xóa.")
        db.close()
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi khi thực hiện hoàn tác: {e}")

async def extract_transaction_info(text: str):
    """Sử dụng Gemini 3.1 Flash Lite bóc tách dữ liệu ra mảng JSON"""
    prompt = f"""
    Bạn là một trợ lý tài chính bóc tách dữ liệu. Nhiệm vụ của bạn là đọc câu văn sau và trích xuất thông tin.
    ĐIỀU KIỆN BẮT BUỘC: Luôn trả về kết quả là MỘT MẢNG JSON (JSON Array) chứa các đối tượng. Dù câu văn chỉ có 1 giao dịch cũng bắt buộc phải bọc trong mảng [].
    KHÔNG giải thích gì thêm, KHÔNG dùng markdown.
    
    Quy tắc phân loại:
    - type: chỉ được là "expense" (chi tiêu) hoặc "income" (thu nhập).
    - category: chọn 1 trong các từ (An_uong, Di_chuyen, Mua_sam, Hoa_don, Giai_tri, Luong, Thu_nhap_khac).
    - amount: số tiền chính xác (chuyển đổi 'k', 'nghìn', 'củ' thành số nguyên). Ví dụ: '50k' -> 50000.
    
    Câu văn: "{text}"
    
    Định dạng JSON bắt buộc phải theo mẫu này:
    [
        {{
            "type": "...",
            "category": "...",
            "amount": 0,
            "note": "mô tả ngắn"
        }}
    ]
    """
    try:
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=prompt
        )
        result_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(result_text)
    except Exception as e:
        print(f"--- LỖI KHI GỌI AI ---")
        print(f"Chi tiết lỗi: {e}")
        return None

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý tin nhắn văn bản thông thường từ người dùng"""
    text = update.message.text
    processing_msg = await update.message.reply_text("⏳ Đang phân tích dữ liệu...")
    
    data = await extract_transaction_info(text)
    
    if data and isinstance(data, list):
        try:
            db = SessionLocal()
            reply_msg = "✅ <b>Đã ghi nhận các giao dịch sau vào CSDL Cloud:</b>\n\n"
            
            for item in data:
                new_transaction = Transaction(
                    user_id=str(update.message.from_user.id),
                    amount=item['amount'],
                    category=item['category'],
                    type=item['type'],
                    note=item['note']
                )
                db.add(new_transaction)
                
                icon = '🔴' if item['type'] == 'expense' else '🟢'
                reply_msg += f"{icon} {item['category']}: <b>{item['amount']:,} VNĐ</b> <i>({item['note']})</i>\n"
                
            db.commit()
            db.close()
        except Exception as e:
            reply_msg = f"❌ Nhận diện được nhưng lỗi lưu Database: {e}"
            print(f"Lỗi DB: {e}")
    else:
        reply_msg = "❌ Lỗi hệ thống: AI không thể bóc tách câu này hoặc định dạng bị sai."
    
    await processing_msg.edit_text(reply_msg, parse_mode='HTML')

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Bộ bắt lỗi tập trung nhằm tránh việc bot bị văng khi mất kết nối mạng đột ngột"""
    print(f"⚠️ Hệ thống gặp sự cố nhỏ: {context.error}")

async def post_init(application: Application):
    """Tự động cài đặt danh sách lệnh gợi ý khi bot khởi động"""
    commands = [
        BotCommand("start", "Khởi động bot Quản gia Tài chính"),
        BotCommand("thongke", "Xem báo cáo thu chi tháng này"),
        BotCommand("lichsu", "Xem nhật ký chi tiết các khoản thu chi"),
        BotCommand("undo", "Xóa nhanh giao dịch vừa nhập")
    ]
    await application.bot.set_my_commands(commands)


if __name__ == '__main__':
    # Kích hoạt web server lách luật chạy trước
    print("Đang bật web server giả để giữ kết nối Render...")
    keep_alive()
    
    print("Khởi động Finance AI Bot...")
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    # Đăng ký các bộ lắng nghe lệnh và tin nhắn
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("thongke", thongke_command))
    app.add_handler(CommandHandler("undo", undo_command))
    app.add_handler(CommandHandler("lichsu", lichsu_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    
    # Đăng ký bộ xử lý lỗi mạng ngầm
    app.add_error_handler(error_handler)

    print("Bot đang lắng nghe tin nhắn...")
    app.run_polling()