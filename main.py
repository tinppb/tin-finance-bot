import os
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai 
from database import SessionLocal, Transaction
from datetime import datetime

# Load các biến môi trường
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Khởi tạo Client của Gemini theo chuẩn mới
client = genai.Client(api_key=GEMINI_API_KEY)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name
    await update.message.reply_text(
        f"Chào {user_name}! Mình là Quản gia Tài chính AI.\n"
        "Cứ nhắn tự nhiên như: 'Sáng nay đổ xăng 50k' hoặc 'Mới nhận lương 10 củ'."
    )

async def undo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xóa giao dịch vừa nhập gần nhất"""
    user_id = str(update.message.from_user.id)
    
    try:
        db = SessionLocal()
        # Tìm giao dịch cuối cùng của user này, sắp xếp theo ID giảm dần
        last_tx = db.query(Transaction).filter(Transaction.user_id == user_id).order_by(Transaction.id.desc()).first()
        
        if last_tx:
            # Lưu lại thông tin trước khi xóa để báo cáo
            thong_tin_xoa = f"{last_tx.category} ({last_tx.amount:,.0f} VNĐ)"
            
            # Xóa khỏi DB
            db.delete(last_tx)
            db.commit()
            
            await update.message.reply_text(f"⏪ <b>Đã hoàn tác (Undo)!</b>\nĐã xóa giao dịch: <i>{thong_tin_xoa}</i>", parse_mode='HTML')
        else:
            await update.message.reply_text("❌ Bạn chưa có giao dịch nào trong sổ tay để xóa.")
            
        db.close()
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi khi xóa dữ liệu: {e}")


async def thongke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tính tổng thu chi trong tháng hiện tại"""
    user_id = str(update.message.from_user.id)
    now = datetime.now()
    
    # Mở DB và lấy tất cả giao dịch của user này
    db = SessionLocal()
    transactions = db.query(Transaction).filter(Transaction.user_id == user_id).all()
    db.close()
    
    tong_thu = 0
    tong_chi = 0
    chi_tiet_chi = {}
    
    # Quét qua dữ liệu để tính toán
    for t in transactions:
        # Chỉ lấy dữ liệu của tháng và năm hiện tại
        if t.created_at.month == now.month and t.created_at.year == now.year:
            if t.type == 'income':
                tong_thu += t.amount
            elif t.type == 'expense':
                tong_chi += t.amount
                # Cộng dồn tiền theo từng danh mục
                if t.category in chi_tiet_chi:
                    chi_tiet_chi[t.category] += t.amount
                else:
                    chi_tiet_chi[t.category] = t.amount
    
    # Định dạng tin nhắn báo cáo
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

async def extract_transaction_info(text: str):
    """Sử dụng Gemini để trích xuất thông tin thu chi ra định dạng JSON"""
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
        # Làm sạch chuỗi trả về
        result_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(result_text)
    except Exception as e:
        print(f"--- LỖI KHI GỌI AI ---")
        print(f"Chi tiết lỗi: {e}")
        return None

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    processing_msg = await update.message.reply_text("⏳ Đang phân tích dữ liệu...")
    
    data = await extract_transaction_info(text)
    
    # Kiểm tra xem AI có trả về dữ liệu và dữ liệu đó có phải là list (danh sách) không
    if data and isinstance(data, list):
        try:
            db = SessionLocal()
            reply_msg = "✅ <b>Đã ghi nhận các giao dịch sau vào CSDL:</b>\n\n"
            
            # Dùng vòng lặp for để duyệt qua từng khoản thu/chi AI bóc được
            for item in data:
                new_transaction = Transaction(
                    user_id=str(update.message.from_user.id),
                    amount=item['amount'],
                    category=item['category'],
                    type=item['type'],
                    note=item['note']
                )
                db.add(new_transaction)
                
                # Cộng dồn vào tin nhắn báo cáo
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
if __name__ == '__main__':
    print("Khởi động Finance AI Bot (Phiên bản Google GenAI mới)...")
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("thongke", thongke_command)) # <--- THÊM DÒNG NÀY VÀO ĐÂY
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CommandHandler("undo", undo_command))

    print("Bot đang lắng nghe tin nhắn...")
    app.run_polling()