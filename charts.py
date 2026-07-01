import matplotlib
matplotlib.use('Agg')  # Chạy headless, không cần GUI
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
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


def format_vnd(amount):
    """Format số tiền VNĐ cho dễ đọc trên biểu đồ."""
    if amount >= 1_000_000:
        return f"{amount / 1_000_000:.1f}tr"
    elif amount >= 1_000:
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
