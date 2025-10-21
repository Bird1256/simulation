# ============================================
# main.py — Finance Simulation API (SimPy Improved with Smart Advice + Dashboard Summary)
# ============================================
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
import simpy, random

from database import SessionLocal, Base, engine, User, FinanceRecord

# ----------------------------
# ✅ Database Setup
# ----------------------------
Base.metadata.create_all(bind=engine)
print("✅ Database checked and ready (finance.db)")

app = FastAPI(title="Finance Simulation API (Smart Advice)", version="3.4")

# ----------------------------
# 🌐 CORS
# ----------------------------
origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:8001"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# ⚙️ Database Dependency
# ----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------------------
# 📥 Models
# ----------------------------
class ExpenseInput(BaseModel):
    house: float
    car: float
    food: float
    saving: float
    travel: float

class SimulationInput(BaseModel):
    name: str
    income: float
    expenses: ExpenseInput

# ----------------------------
# 💡 Smart Financial Advice
# ----------------------------
def generate_advice(income: float, expenses: dict):
    advice = []
    total_expense = sum(expenses.values())
    saving = expenses.get("saving", 0)

    # 1️⃣ รายจ่ายมากกว่ารายรับ
    if total_expense > income:
        advice.append("❌ รายจ่ายมากกว่ารายรับ ควรลดค่าใช้จ่ายบางส่วนเพื่อป้องกันการขาดสภาพคล่องทางการเงิน")

    # 2️⃣ เงินออม < 10% ของรายได้
    if saving < (0.10 * income):
        advice.append("💡 ควรเพิ่มเงินออมอย่างน้อย 10% ของรายได้ต่อเดือน เพื่อสร้างความมั่นคง")

    # 3️⃣ ค่าบ้าน > 35% หรือ > 17,500
    if expenses.get("house", 0) > 0.35 * income or expenses.get("house", 0) > 17500:
        advice.append("🏠 ค่าที่อยู่อาศัยสูงเกินไป ควรลดค่าเช่าหรือรีไฟแนนซ์บ้าน")

    # 4️⃣ ค่าเดินทาง > 20% หรือ > 3,000
    if expenses.get("car", 0) > 0.20 * income or expenses.get("car", 0) > 3000:
        advice.append("🚗 ค่าเดินทางสูงเกินไป แนะนำใช้ขนส่งสาธารณะหรือปรับเส้นทางเพื่อลดค่าน้ำมัน")

    # 5️⃣ ค่าอาหาร > 30% หรือ > 5,000
    if expenses.get("food", 0) > 0.30 * income or expenses.get("food", 0) > 5000:
        advice.append("🍛 ค่าอาหารเกินเกณฑ์ แนะนำทำอาหารกินเองหรือลดการสั่งอาหารเดลิเวอรี่")

    # 6️⃣ ค่าเที่ยว > 10,000
    if expenses.get("travel", 0) > 10000:
        advice.append("✈️ ค่าใช้จ่ายท่องเที่ยวสูงเกินไป ควรจำกัดงบประมาณในแต่ละเดือน")

    # ✅ ถ้าไม่มีปัญหา
    if not advice:
        advice.append("✅ เยี่ยมมาก! การใช้จ่ายของคุณสมดุลและมีการออมเหมาะสม 👍")

    return " ".join(advice)

# ----------------------------
# ⚙️ SimPy Simulation (12 เดือน)
# ----------------------------
def simulate_with_simpy(income, expenses):
    env = simpy.Environment()
    results = []

    def monthly_process(env, months, income, expenses):
        cumulative = 0
        for i in range(1, months + 1):
            yield env.timeout(0.1)
            monthly_expense = sum(expenses.values())
            monthly_income = income + random.uniform(-500, 1000)
            monthly_balance = monthly_income - monthly_expense
            cumulative += monthly_balance
            results.append({
                "month": f"เดือนที่ {i}",
                "balance": round(monthly_balance, 2),
                "cumulative_saving": round(cumulative, 2)
            })

    env.process(monthly_process(env, 12, income, expenses))
    env.run()
    return results

# ----------------------------
# 🚀 API: /simulate
# ----------------------------
@app.post("/simulate")
def simulate(data: SimulationInput, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.name == data.name).first()
    if not user:
        user = User(name=data.name)
        db.add(user)
        db.commit()
        db.refresh(user)

    income = data.income
    expenses = data.expenses.dict()

    monthly_result = simulate_with_simpy(income, expenses)
    total_expense = sum(expenses.values())
    monthly_balance = income - total_expense
    total_saving = monthly_balance * 12
    advice = generate_advice(income, expenses)

    record = FinanceRecord(
        user_id=user.id,
        month=datetime.now().strftime("%Y-%m"),
        income=income,
        house=expenses["house"],
        car=expenses["car"],
        food=expenses["food"],
        saving=expenses["saving"],
        travel=expenses["travel"],
        total_expense=total_expense,
        balance=monthly_balance,
        cumulative_saving=total_saving,
        created_at=datetime.now(),
        detail=str(advice)
    )
    db.add(record)
    db.commit()

    return JSONResponse(content={
        "summary": {
            "name": user.name,
            "monthly_income": income,
            "monthly_expense": total_expense,
            "monthly_balance": monthly_balance,
            "total_saving_12m": total_saving,
            "expenses": expenses,
            "advice": advice
        },
        "simulation_result": monthly_result
    })

# ----------------------------
# 🕒 API: /history/{name}
# ----------------------------
@app.get("/history/{name}")
def get_history(name: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.name == name).first()
    if not user:
        raise HTTPException(status_code=404, detail="ไม่พบผู้ใช้นี้")

    records = db.query(FinanceRecord).filter(FinanceRecord.user_id == user.id).all()
    data = [{
        "month": r.month,
        "income": r.income,
        "total_expense": r.total_expense,
        "balance": r.balance,
        "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "detail": r.detail
    } for r in records]

    return JSONResponse(content={"user": user.name, "records": data})

# ----------------------------
# 🧭 API: รายชื่อผู้ใช้ทั้งหมด + คำแนะนำล่าสุด
# ----------------------------
@app.get("/history/summary")
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    result = []
    for u in users:
        last_record = (
            db.query(FinanceRecord)
            .filter(FinanceRecord.user_id == u.id)
            .order_by(FinanceRecord.created_at.desc())
            .first()
        )
        result.append({
            "name": u.name,
            "latest_advice": last_record.detail if last_record else "ยังไม่มีข้อมูลจำลอง"
        })
    return {"users": [r["name"] for r in result], "details": result}

# ----------------------------
# 🌍 Root Endpoint
# ----------------------------
@app.get("/")
def root():
    return JSONResponse(content={"message": "💰 Finance Simulation API (Smart Advice + Summary) is running successfully!"})
