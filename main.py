import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from telegram import BotCommand

# Import cấu hình Database từ file database.py
from database import SessionLocal, Transaction, get_db, get_transactions_by_month, get_transactions_by_year
# Import module tạo biểu đồ
from charts import generate_monthly_chart, generate_yearly_overview_chart
# Import bộ giữ mạng sống từ file keep_alive.py
from keep_alive import keep_alive

# Load các biến môi trường (.env trên máy local hoặc Environment Variables trên Render)
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Khởi tạo Client Gemini thế hệ mới
client = genai.Client(api_key=GEMINI_API_KEY)


def parse_month_year(args):
    """
    Parse tham số tháng/năm từ lệnh Telegram.
    Ví dụ:
        /thongke         -> tháng hiện tại
        /thongke 6       -> tháng 6, năm hiện tại
        /thongke 3 2025  -> tháng 3, năm 2025
    Trả về (month, year) hoặc raise ValueError nếu không hợp lệ.
    """
    now = datetime.now()
    
    if not args or len(args) == 0:
        return now.month, now.year
    
    try:
        month = int(args[0])
        if month < 1 or month > 12:
            raise ValueError("Tháng phải từ 1 đến 12")
        
        if len(args) >= 2:
            year = int(args[1])
            if year < 2020 or year > 2030:
                raise ValueError("Năm phải từ 2020 đến 2030")
        else:
            year = now.year
        
        return month, year
    except (ValueError, IndexError) as e:
        if "Tháng" in str(e) or "Năm" in str(e):
            raise
        raise ValueError("Sai cú pháp! Dùng: /lệnh [tháng] [năm]\nVí dụ: /thongke 6 hoặc /thongke 3 2025")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /start khi người dùng bắt đầu chat với bot"""
    user_name = update.message.from_user.first_name
    await update.message.reply_text(
        f"Chào {user_name}! Mình là Quản gia Tài chính AI.\n"
        "Cứ nhắn tự nhiên như: 'Sáng ăn bún bò 45k, đổ xăng 50k' hoặc 'Mới nhận lương làm thêm 3 củ'.\n\n"
        "Các lệnh có sẵn:\n"
        "📊 /thongke - Xem báo cáo thu chi tháng này\n"
        "📜 /lichsu - Xem nhật ký chi tiết các khoản thu chi\n"
        "📈 /bieuedo - Xem biểu đồ thống kê thu chi\n"
        "📉 /tonghop - Biểu đồ tổng hợp thu chi cả năm\n"
        "⏪ /undo - Xóa nhanh giao dịch vừa nhập\n\n"
        "💡 <b>Mẹo:</b> Thêm số tháng sau lệnh để xem tháng khác!\n"
        "Ví dụ: <code>/thongke 6</code> hoặc <code>/lichsu 3 2025</code>\n"
        "Xem năm khác: <code>/tonghop 2025</code>",
        parse_mode='HTML'
    )

async def thongke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /thongke tính tổng thu chi theo tháng từ Cloud DB"""
    user_id = str(update.message.from_user.id)
    
    try:
        month, year = parse_month_year(context.args)
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
        return
    
    try:
        transactions = get_transactions_by_month(user_id, month, year)
        
        tong_thu = 0
        tong_chi = 0
        chi_tiet_chi = {}
        
        for t in transactions:
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
        msg = f"📊 <b>BÁO CÁO THÁNG {month}/{year}</b>\n\n"
        msg += f"🟢 Tổng thu: <b>{tong_thu:,.0f} VNĐ</b>\n"
        msg += f"🔴 Tổng chi: <b>{tong_chi:,.0f} VNĐ</b>\n"
        msg += f"-----------------------\n"
        msg += f"<b>Chi tiết các khoản chi:</b>\n"
        
        if not chi_tiet_chi:
            msg += f"<i>Chưa có khoản chi nào trong tháng {month}/{year}.</i>\n"
        else:
            for cat, amount in chi_tiet_chi.items():
                msg += f"  - {cat}: {amount:,.0f} VNĐ\n"
                
        msg += f"\n💰 <b>Số dư tháng này: {(tong_thu - tong_chi):,.0f} VNĐ</b>"
        
        await update.message.reply_text(msg, parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi khi lấy dữ liệu thống kê: {e}")

async def lichsu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Liệt kê TOÀN BỘ danh sách chi tiết các giao dịch theo tháng"""
    user_id = str(update.message.from_user.id)
    
    try:
        month, year = parse_month_year(context.args)
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
        return
    
    try:
        transactions = get_transactions_by_month(user_id, month, year)
        
        # Tạo một mảng để chứa các đoạn tin nhắn (tránh bị quá giới hạn của Telegram)
        messages = []
        current_msg = f"📜 <b>NHẬT KÝ CHI TIÊU THÁNG {month}/{year}</b>\n"
        current_msg += "---------------------------------\n"
        
        count = 0
        for t in transactions:
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
            current_msg += f"<i>Chưa có giao dịch nào được ghi nhận trong tháng {month}/{year}.</i>"
            
        # Đưa đoạn tin nhắn cuối cùng vào mảng
        messages.append(current_msg)
        
        # Vòng lặp gửi lần lượt từng tin nhắn trong mảng cho người dùng
        for m in messages:
            if m.strip(): # Chỉ gửi nếu tin nhắn có nội dung
                await update.message.reply_text(m, parse_mode='HTML')
                
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi khi lấy nhật ký chi tiêu: {e}")

async def bieuedo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /bieuedo gửi biểu đồ thống kê thu chi dưới dạng ảnh"""
    user_id = str(update.message.from_user.id)
    
    try:
        month, year = parse_month_year(context.args)
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
        return
    
    processing_msg = await update.message.reply_text("⏳ Đang tạo biểu đồ...")
    
    try:
        transactions = get_transactions_by_month(user_id, month, year)
        
        tong_thu = 0
        tong_chi = 0
        chi_tiet_chi = {}
        
        for t in transactions:
            if t.type == 'income':
                tong_thu += t.amount
            elif t.type == 'expense':
                tong_chi += t.amount
                if t.category in chi_tiet_chi:
                    chi_tiet_chi[t.category] += t.amount
                else:
                    chi_tiet_chi[t.category] = t.amount
        
        if tong_thu == 0 and tong_chi == 0:
            await processing_msg.edit_text(
                f"📈 Chưa có dữ liệu nào trong tháng {month}/{year} để tạo biểu đồ."
            )
            return
        
        # Tạo biểu đồ
        chart_image = generate_monthly_chart(tong_thu, tong_chi, chi_tiet_chi, month, year)
        
        # Gửi ảnh biểu đồ cho user
        await update.message.reply_photo(
            photo=chart_image,
            caption=f"📈 Biểu đồ thu chi tháng {month}/{year}"
        )
        
        # Xóa tin nhắn "Đang tạo biểu đồ..."
        await processing_msg.delete()
        
    except Exception as e:
        await processing_msg.edit_text(f"❌ Lỗi khi tạo biểu đồ: {e}")

async def tonghop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /tonghop gửi biểu đồ tổng hợp thu chi cả năm (mỗi tháng 2 cột Thu/Chi)"""
    user_id = str(update.message.from_user.id)
    now = datetime.now()
    
    # Parse năm từ tham số (mặc định năm hiện tại)
    try:
        if context.args and len(context.args) >= 1:
            year = int(context.args[0])
            if year < 2020 or year > 2030:
                raise ValueError("Năm phải từ 2020 đến 2030")
        else:
            year = now.year
    except ValueError as e:
        if "Năm" in str(e):
            await update.message.reply_text(f"❌ {e}")
        else:
            await update.message.reply_text("❌ Sai cú pháp! Dùng: /tonghop [năm]\nVí dụ: /tonghop 2025")
        return
    
    processing_msg = await update.message.reply_text("⏳ Đang tạo biểu đồ tổng hợp...")
    
    try:
        transactions = get_transactions_by_year(user_id, year)
        
        if not transactions:
            await processing_msg.edit_text(
                f"📉 Chưa có dữ liệu nào trong năm {year} để tạo biểu đồ tổng hợp."
            )
            return
        
        # Gom dữ liệu theo tháng
        monthly_data = {}
        for t in transactions:
            m = t.created_at.month
            if m not in monthly_data:
                monthly_data[m] = {'thu': 0, 'chi': 0}
            if t.type == 'income':
                monthly_data[m]['thu'] += t.amount
            elif t.type == 'expense':
                monthly_data[m]['chi'] += t.amount
        
        # Tạo biểu đồ tổng hợp
        chart_image = generate_yearly_overview_chart(monthly_data, year)
        
        await update.message.reply_photo(
            photo=chart_image,
            caption=f"📉 Biểu đồ tổng hợp thu chi năm {year}"
        )
        
        await processing_msg.delete()
        
    except Exception as e:
        await processing_msg.edit_text(f"❌ Lỗi khi tạo biểu đồ tổng hợp: {e}")

async def undo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /undo xóa giao dịch vừa nhập gần nhất của user"""
    user_id = str(update.message.from_user.id)
    
    try:
        with get_db() as db:
            # Tìm giao dịch cuối cùng của user (ID lớn nhất)
            last_tx = db.query(Transaction).filter(Transaction.user_id == user_id).order_by(Transaction.id.desc()).first()
            
            if last_tx:
                thong_tin_xoa = f"{last_tx.category} ({last_tx.amount:,.0f} VNĐ)"
                db.delete(last_tx)
                db.commit()
                await update.message.reply_text(f"⏪ <b>Đã hoàn tác (Undo)!</b>\nĐã xóa dữ liệu: <i>{thong_tin_xoa}</i>", parse_mode='HTML')
            else:
                await update.message.reply_text("❌ Bạn chưa có giao dịch nào gần đây để xóa.")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi khi thực hiện hoàn tác: {e}")

async def extract_transaction_info(text: str):
    """Sử dụng Gemini 2.0 Flash Lite bóc tách dữ liệu ra mảng JSON (có retry)"""
    prompt = f"""Bạn là một trợ lý tài chính bóc tách dữ liệu. Nhiệm vụ của bạn là đọc câu văn sau và trích xuất thông tin.

ĐIỀU KIỆN BẮT BUỘC:
- Luôn trả về kết quả là MỘT MẢNG JSON (JSON Array) []. Dù chỉ có 1 giao dịch cũng phải bọc trong [].
- CHỈ trả về JSON thuần, KHÔNG giải thích, KHÔNG dùng markdown, KHÔNG bọc trong ```json```.

Quy tắc phân loại:
- type: "expense" (chi tiêu) hoặc "income" (thu nhập).
- category: chọn 1 trong các danh mục sau:
  + An_uong: ăn uống, nhậu, cà phê, trà sữa, ăn sáng/trưa/tối, uống nước
  + Di_chuyen: xăng, xe, grab, taxi, gửi xe, vé tàu/xe/máy bay
  + Mua_sam: mua đồ, quần áo, giày dép, sách, đồ dùng học tập, văn phòng phẩm, đồ gia dụng
  + Hoa_don: điện, nước, internet, điện thoại, học phí, tiền nhà, nộp quỹ
  + Giai_tri: xem phim, ca nhạc, du lịch, game, gym, đi nhảy, thể thao, đá bóng
  + Luong: lương, thưởng chính thức
  + Thu_nhap_khac: freelance, bán đồ, tiền thưởng, tiền cho/biếu
- amount: số tiền chính xác (số nguyên, đơn vị VNĐ).

Quy tắc chuyển đổi số tiền:
- "50k" hoặc "50K" → 50000
- "3 củ" hoặc "3 triệu" → 3000000
- "50 nghìn" → 50000
- "40.000" hoặc "40,000" → 40000 (dấu chấm/phẩy là phân cách hàng nghìn)
- "100.000" → 100000
- Nếu chỉ có số không có đơn vị (ví dụ: "25", "30"), hiểu là nghìn VNĐ → nhân 1000.

Câu văn: "{text}"

Lưu ý: Câu văn có thể chứa nhiều giao dịch ngăn cách bằng dấu chấm phẩy (;) hoặc dấu phẩy. Mỗi giao dịch là 1 object trong mảng JSON.
Ví dụ input: "Xem phim 80k; Ăn sáng 25k; Uống cf 12k" → trả về mảng 3 phần tử.

[{{"type": "...", "category": "...", "amount": 0, "note": "mô tả ngắn"}}]"""

    max_retries = 3
    last_error = None
    last_raw = None
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash-lite',
                contents=prompt
            )
            raw_text = response.text
            last_raw = raw_text
            
            # Parse JSON từ response (xử lý nhiều trường hợp bẩn)
            result = extract_json_from_text(raw_text)
            if result is not None:
                return result
            
            print(f"--- LẦN THỬ {attempt + 1}: AI trả về nhưng không parse được JSON ---")
            print(f"Raw response: {raw_text[:500]}")
            
        except Exception as e:
            last_error = e
            print(f"--- LẦN THỬ {attempt + 1}: LỖI KHI GỌI AI ---")
            print(f"Chi tiết lỗi: {e}")
    
    # Sau 3 lần thử vẫn lỗi
    print(f"=== THẤT BẠI SAU {max_retries} LẦN THỬ ===")
    print(f"Input: {text}")
    if last_raw:
        print(f"Raw response cuối: {last_raw[:500]}")
    if last_error:
        print(f"Lỗi cuối: {last_error}")
    return None


def extract_json_from_text(text: str):
    """
    Trích xuất mảng JSON từ response AI, xử lý nhiều trường hợp bẩn:
    - Response có text thừa trước/sau JSON
    - Response bọc trong ```json ... ```
    - Response có dấu xuống dòng, khoảng trắng thừa
    """
    if not text:
        return None
    
    # Bước 1: Loại bỏ markdown code block
    cleaned = text.strip()
    cleaned = cleaned.replace('```json', '').replace('```JSON', '').replace('```', '')
    cleaned = cleaned.strip()
    
    # Bước 2: Thử parse trực tiếp
    try:
        result = json.loads(cleaned)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass
    
    # Bước 3: Dùng regex tìm mảng JSON [...] trong text
    match = re.search(r'\[[\s\S]*\]', cleaned)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass
    
    return None


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý tin nhắn văn bản thông thường từ người dùng"""
    raw_text = update.message.text
    
    # Chuẩn hóa input: thay xuống dòng bằng dấu chấm phẩy để AI xử lý được nhiều giao dịch trên 1 tin nhắn
    text = raw_text.replace('\n', '; ').strip()
    
    processing_msg = await update.message.reply_text("⏳ Đang phân tích dữ liệu...")
    
    data = await extract_transaction_info(text)
    
    if data and isinstance(data, list):
        try:
            with get_db() as db:
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
        except Exception as e:
            reply_msg = f"❌ Nhận diện được nhưng lỗi lưu Database: {e}"
            print(f"Lỗi DB: {e}")
    else:
        reply_msg = (
            "❌ Không thể bóc tách dữ liệu sau 3 lần thử.\n"
            "💡 <b>Mẹo:</b> Thử viết rõ hơn, ví dụ:\n"
            "<code>Ăn phở 25k</code> hoặc <code>Ăn phở 25.000</code>"
        )
    
    await processing_msg.edit_text(reply_msg, parse_mode='HTML')

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Bộ bắt lỗi tập trung nhằm tránh việc bot bị văng khi mất kết nối mạng đột ngột"""
    print(f"⚠️ Hệ thống gặp sự cố nhỏ: {context.error}")

async def post_init(application: Application):
    """Tự động cài đặt danh sách lệnh gợi ý khi bot khởi động"""
    commands = [
        BotCommand("start", "Khởi động bot Quản gia Tài chính"),
        BotCommand("thongke", "Báo cáo thu chi (thêm số tháng để xem tháng khác)"),
        BotCommand("lichsu", "Nhật ký chi tiết (thêm số tháng để xem tháng khác)"),
        BotCommand("bieuedo", "Biểu đồ thống kê thu chi"),
        BotCommand("tonghop", "Biểu đồ tổng hợp thu chi cả năm"),
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
    app.add_handler(CommandHandler("bieuedo", bieuedo_command))
    app.add_handler(CommandHandler("tonghop", tonghop_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    
    # Đăng ký bộ xử lý lỗi mạng ngầm
    app.add_error_handler(error_handler)

    print("Bot đang lắng nghe tin nhắn...")
    app.run_polling()