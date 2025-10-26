# ============================================
# 🗃️ database.py — Database Schema (SQLAlchemy ORM)
# ============================================

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime

# ----------------------------
# 🔗 การเชื่อมต่อฐานข้อมูล
# ----------------------------
DATABASE_URL = "sqlite:///./finance.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ----------------------------
# 👤 ตารางผู้ใช้ (Users)
# ----------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

    # สัมพันธ์กับตารางการเงิน
    records = relationship("FinanceRecord", back_populates="user", cascade="all, delete")

# ----------------------------
# 💰 ตารางบันทึกรายรับรายจ่าย (FinanceRecord)
# ----------------------------
class FinanceRecord(Base):
    __tablename__ = "finance_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    month = Column(String, default="-")
    income = Column(Float)
    house = Column(Float)
    car = Column(Float)
    food = Column(Float)
    saving = Column(Float)
    travel = Column(Float)
    total_expense = Column(Float)
    balance = Column(Float)
    cumulative_saving = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.now)

    # 🔍 เพิ่ม detail เก็บ JSON ของค่าใช้จ่ายรายหมวด
    detail = Column(String, nullable=True)

    # สัมพันธ์กับตารางผู้ใช้
    user = relationship("User", back_populates="records")

# ----------------------------
# 🧱 ฟังก์ชันสร้างตาราง
# ----------------------------
def init_db():
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully (finance.db)")

if __name__ == "__main__":
    init_db()
