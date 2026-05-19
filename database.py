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

# Xóa connect_args={"check_same_thread": False} vì đó là của SQLite
engine = create_engine(SQLALCHEMY_DATABASE_URL)

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