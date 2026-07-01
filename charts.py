import matplotlib
matplotlib.use('Agg')  # Chạy headless, không cần GUI
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from io import BytesIO


# Bảng màu cho các danh mục chi tiêu
CATEGORY_COLORS = {
    'An_uong':       '#FF6B6B',
    'Di_chuyen':     '#4ECDC4',
    'Mua_sam':       '#45B7D1',
    'Hoa_don':       '#FFA07A',
    'Giai_tri':      '#DDA0DD',
    'Luong':         '#98FB98',
    'Thu_nhap_khac': '#87CEEB',
}

# Tên hiển thị tiếng Việt
CATEGORY_LABELS = {
    'An_uong':       'Ăn uống',
    'Di_chuyen':     'Di chuyển',
    'Mua_sam':       'Mua sắm',
    'Hoa_don':       'Hóa đơn',
    'Giai_tri':      'Giải trí',
    'Luong':         'Lương',
    'Thu_nhap_khac': 'Thu nhập khác',
}

DEFAULT_COLOR = '#B0BEC5'

MONTH_NAMES = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12']


def format_vnd(amount):
    """Format số tiền VNĐ cho dễ đọc trên biểu đồ."""
    if abs(amount) >= 1_000_000:
        return f"{amount / 1_000_000:.1f}tr"
    elif abs(amount) >= 1_000:
        return f"{amount / 1_000:.0f}k"
    return f"{amount:.0f}"


def generate_monthly_chart(tong_thu, tong_chi, chi_tiet_chi: dict, month: int, year: int):
    """
    Tạo ảnh biểu đồ tháng gồm Bar Chart (Thu vs Chi) + Pie Chart (Danh mục chi).
    Trả về BytesIO chứa ảnh PNG (sẵn sàng gửi qua Telegram).
    """
    # --- Cấu hình style tối (dark theme) ---
    plt.style.use('dark_background')
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), facecolor='#1a1a2e')
    fig.suptitle(f'📊 THỐNG KÊ THU CHI THÁNG {month}/{year}',
                 fontsize=16, fontweight='bold', color='white', y=0.98)

    # ============================
    # 1. BAR CHART: Tổng thu vs Tổng chi
    # ============================
    ax1 = axes[0]
    ax1.set_facecolor('#16213e')

    categories = ['Thu nhập', 'Chi tiêu']
    amounts = [tong_thu, tong_chi]
    colors = ['#00d2ff', '#ff416c']

    bars = ax1.bar(categories, amounts, color=colors, width=0.5,
                   edgecolor='white', linewidth=0.5, zorder=3)

    # Annotation số tiền lên đầu mỗi cột
    for bar, amount in zip(bars, amounts):
        if amount > 0:
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(amounts) * 0.02,
                     format_vnd(amount), ha='center', va='bottom',
                     fontsize=13, fontweight='bold', color='white')

    ax1.set_title('Tổng Thu vs Tổng Chi', fontsize=12, color='#e0e0e0', pad=10)
    ax1.set_ylabel('VNĐ', fontsize=10, color='#aaa')
    ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: format_vnd(x)))
    ax1.tick_params(colors='#aaa')
    ax1.grid(axis='y', alpha=0.15, color='white')
    ax1.set_axisbelow(True)

    # Thêm dòng số dư
    so_du = tong_thu - tong_chi
    color_du = '#00d2ff' if so_du >= 0 else '#ff416c'
    sign = '+' if so_du >= 0 else ''
    ax1.text(0.5, -0.12, f"💰 Số dư: {sign}{format_vnd(so_du)} VNĐ",
             ha='center', va='top', transform=ax1.transAxes,
             fontsize=11, color=color_du, fontweight='bold')

    # ============================
    # 2. PIE CHART: Chi tiết danh mục chi tiêu
    # ============================
    ax2 = axes[1]
    ax2.set_facecolor('#1a1a2e')

    if chi_tiet_chi:
        labels = []
        sizes = []
        pie_colors = []

        for cat, amount in sorted(chi_tiet_chi.items(), key=lambda x: x[1], reverse=True):
            labels.append(CATEGORY_LABELS.get(cat, cat))
            sizes.append(amount)
            pie_colors.append(CATEGORY_COLORS.get(cat, DEFAULT_COLOR))

        wedges, texts, autotexts = ax2.pie(
            sizes, labels=labels, autopct='%1.1f%%',
            colors=pie_colors, startangle=140,
            textprops={'fontsize': 9, 'color': 'white'},
            pctdistance=0.75, labeldistance=1.12,
            wedgeprops={'edgecolor': '#1a1a2e', 'linewidth': 1.5}
        )
        # In đậm phần trăm
        for autotext in autotexts:
            autotext.set_fontweight('bold')
            autotext.set_fontsize(9)

        ax2.set_title('Tỷ lệ các khoản chi', fontsize=12, color='#e0e0e0', pad=10)
    else:
        ax2.text(0.5, 0.5, 'Chưa có\nkhoản chi nào', ha='center', va='center',
                 fontsize=14, color='#888', style='italic',
                 transform=ax2.transAxes)
        ax2.set_title('Tỷ lệ các khoản chi', fontsize=12, color='#e0e0e0', pad=10)

    # --- Xuất ảnh ra BytesIO ---
    plt.tight_layout(rect=[0, 0.03, 1, 0.93])
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor(), edgecolor='none')
    buf.seek(0)
    plt.close(fig)

    return buf


def generate_yearly_overview_chart(monthly_data: dict, year: int):
    """
    Tạo biểu đồ cột tổng hợp cả năm: mỗi tháng có 2 cột Thu (xanh) và Chi (đỏ).
    
    Args:
        monthly_data: dict dạng {month: {'thu': float, 'chi': float}}
        year: năm hiển thị
    
    Trả về BytesIO chứa ảnh PNG.
    """
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(14, 6), facecolor='#1a1a2e')
    ax.set_facecolor('#16213e')

    # Chuẩn bị dữ liệu cho 12 tháng
    thu_values = []
    chi_values = []
    for m in range(1, 13):
        data = monthly_data.get(m, {'thu': 0, 'chi': 0})
        thu_values.append(data['thu'])
        chi_values.append(data['chi'])

    x = np.arange(12)  # Vị trí các tháng
    bar_width = 0.35    # Độ rộng mỗi cột

    # Vẽ 2 nhóm cột: Thu (xanh) và Chi (đỏ)
    bars_thu = ax.bar(x - bar_width/2, thu_values, bar_width,
                      label='Thu nhập', color='#00d2ff',
                      edgecolor='white', linewidth=0.3, zorder=3)
    bars_chi = ax.bar(x + bar_width/2, chi_values, bar_width,
                      label='Chi tiêu', color='#ff416c',
                      edgecolor='white', linewidth=0.3, zorder=3)

    # Annotation số tiền lên đầu mỗi cột (chỉ hiện nếu > 0)
    for bar in bars_thu:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, h,
                    format_vnd(h), ha='center', va='bottom',
                    fontsize=7, fontweight='bold', color='#00d2ff', rotation=45)
    for bar in bars_chi:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, h,
                    format_vnd(h), ha='center', va='bottom',
                    fontsize=7, fontweight='bold', color='#ff416c', rotation=45)

    # Cấu hình trục & style
    ax.set_xlabel('Tháng', fontsize=11, color='#ccc')
    ax.set_ylabel('VNĐ', fontsize=11, color='#ccc')
    ax.set_title(f'📊 TỔNG HỢP THU CHI NĂM {year}',
                 fontsize=16, fontweight='bold', color='white', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(MONTH_NAMES, fontsize=10, color='#ddd')
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: format_vnd(v)))
    ax.tick_params(colors='#aaa')
    ax.grid(axis='y', alpha=0.15, color='white')
    ax.set_axisbelow(True)
    ax.legend(loc='upper right', fontsize=10, facecolor='#16213e',
              edgecolor='#444', labelcolor='white')

    # Dòng tổng kết ở dưới
    total_thu = sum(thu_values)
    total_chi = sum(chi_values)
    so_du = total_thu - total_chi
    color_du = '#00d2ff' if so_du >= 0 else '#ff416c'
    sign = '+' if so_du >= 0 else ''

    summary = (f"🟢 Tổng thu cả năm: {format_vnd(total_thu)} VNĐ    |    "
               f"🔴 Tổng chi cả năm: {format_vnd(total_chi)} VNĐ    |    "
               f"💰 Số dư: {sign}{format_vnd(so_du)} VNĐ")
    fig.text(0.5, 0.01, summary, ha='center', va='bottom',
             fontsize=10, color=color_du, fontweight='bold')

    # --- Xuất ảnh ---
    plt.tight_layout(rect=[0, 0.05, 1, 0.97])
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor(), edgecolor='none')
    buf.seek(0)
    plt.close(fig)

    return buf

