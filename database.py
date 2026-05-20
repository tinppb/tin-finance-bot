import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Lấy đường dẫn DB từ biến môi trường
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Vá lỗi nhỏ: SQLAlchemy bản mới bắt buộc dùng 'postgresql://' thay vì 'postgres://'
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)


engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=5,          # Giữ tối đa 5 kết nối mở sẵn
    max_overflow=10,      # Cho phép mở thêm tối đa 10 kết nối nếu quá tải
    pool_timeout=30,      # Chờ tối đa 30 giây để lấy kết nối
    pool_recycle=1800,    # Tự động xóa kết nối cũ sau 30 phút để tránh bị Neon ngắt ngầm
    pool_pre_ping=True    # CHÌA KHÓA VÀNG: Trước khi chạy lệnh, "nhá máy" (ping) thử xem đường ống còn sống không. Nếu chết thì tự tạo cái mới luôn!
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Bảng dữ liệu giữ nguyên không đổi 1 chữ nào ---
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    amount = Column(Float)
    category = Column(String)
    type = Column(String) 
    note = Column(String)
    created_at = Column(DateTime, default=datetime.now)

# Tạo bảng tự động trên server Neon
Base.metadata.create_all(bind=engine)