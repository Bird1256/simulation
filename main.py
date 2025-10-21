# ============================================
# main.py — Finance Simulation API (SimPy Improved)
# ============================================
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
import simpy, random, time

from database import SessionLocal, Base, engine, User, FinanceRecord

# ----------------------------
# ✅ สร้างตารางถ้ายังไม่มี
# ----------------------------
Base.metadata.create_all(bind=engine)
print("✅ Database checked and ready (finance.db)")

app = FastAPI(title="Finance Simulation API (SimPy)", version="3.2")

# ----------------------------
# 🌐 ตั้งค่า CORS
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
# ⚙️ DB Dependency
# ----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------------------
# 📥 Input Models
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
# 💬 Generate Advice
# ----------------------------
def generate_advice(income: float, expenses: dict):
    total_exp = sum(expenses.values())
    saving = expenses.get("saving", 0)

    if total_exp > income:
        return "❌ รายจ่ายมากกว่ารายรับ ควรลดค่าใช้จ่ายบางส่วน เช่น ค่าอาหารหรือค่าเดินทาง"
    elif saving < income * 0.1:
        return "💡 ควรเพิ่มเงินเก็บอย่างน้อย 10% ของรายได้ต่อเดือน"
    elif expenses["food"] > income * 0.3:
        return "🍱 ค่าอาหารสูงเกินไป ควรทำอาหารเองเพื่อลดค่าใช้จ่าย"
    elif expenses["travel"] > income * 0.2:
        return "✈️ ค่าเดินทางสูงเกินไป ควรจำกัดให้อยู่ไม่เกิน 20% ของรายได้"
    elif expenses["car"] > income * 0.25:
        return "🚗 ค่าใช้จ่ายรถยนต์สูง ลองใช้ขนส่งสาธารณะบางส่วน"
    elif expenses["house"] > income * 0.35:
        return "🏠 ค่าเช่าบ้านสูงเกิน 35% ของรายได้"
    else:
        return "✅ เยี่ยมมาก! การใช้จ่ายของคุณสมดุลและมีการออมเหมาะสม"

# ----------------------------
# ⚙️ SimPy Simulation (12 เดือน)
# ----------------------------
def simulate_with_simpy(income, expenses):
    env = simpy.Environment()
    results = []

    def monthly_process(env, months, income, expenses):
        cumulative = 0
        for i in range(1, months + 1):
            yield env.timeout(0.1)  # เพิ่ม delay เล็กน้อย
            monthly_expense = sum(expenses.values())
            monthly_income = income + random.uniform(-500, 1000)  # เพิ่มความผันผวนรายได้
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
# 🚀 /simulate API
# ----------------------------
@app.post("/simulate")
def simulate(data: SimulationInput, db: Session = Depends(get_db)):
    # ตรวจว่ามีผู้ใช้นี้หรือยัง
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
        detail=str(expenses)
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
            "expenses": expenses,   # ✅ ใช้ key ตรงกับ script.js
            "advice": advice
        },
        "simulation_result": monthly_result
    })

# ----------------------------
# 🕒 /history API
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
        "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S")
    } for r in records]

    return JSONResponse(content={"user": user.name, "records": data})

@app.get("/")
def root():
    return JSONResponse(content={"message": "💰 Finance Simulation API (SimPy) is running successfully!"})
