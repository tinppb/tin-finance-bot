from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime

Base = declarative_base()

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, index=True) # ID Telegram của người dùng
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False) 
    type = Column(String, nullable=False) # 'expense' hoặc 'income'
    note = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# Tạo file SQLite local
engine = create_engine('sqlite:///finance.db', echo=False)
Base.metadata.create_all(engine)

SessionLocal = sessionmaker(bind=engine)