# ======================================================
# main.py — เวอร์ชันซ่อมฐานข้อมูล + รองรับ summary แน่นอน
# ======================================================
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
import simpy, random
from database import SessionLocal, Base, engine, User, FinanceRecord

# ======================================================
# ✅ Database setup
# ======================================================
Base.metadata.create_all(bind=engine)
print("✅ Database checked and ready (finance.db)")

app = FastAPI(title="Finance Simulation API", version="5.0")

# ======================================================
# 🌐 CORS
# ======================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# ⚙️ Dependency
# ======================================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ======================================================
# 📥 Models
# ======================================================
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

# ======================================================
# 💡 Smart advice
# ======================================================
def generate_advice(income, expenses):
    advice = []
    total = sum(expenses.values())
    saving = expenses.get("saving", 0)

    if total > income:
        advice.append("❌ รายจ่ายมากกว่ารายรับ ควรลดค่าใช้จ่ายบางส่วน")
    if saving < 0.1 * income:
        advice.append("💡 ควรออมอย่างน้อย 10% ของรายได้")
    if expenses["house"] > 0.35 * income:
        advice.append("🏠 ค่าบ้านสูงเกินไป ควรลดหรือรีไฟแนนซ์")
    if expenses["car"] > 0.2 * income:
        advice.append("🚗 ค่าเดินทางสูง แนะนำใช้ขนส่งสาธารณะ")
    if expenses["food"] > 0.3 * income:
        advice.append("🍛 ค่าอาหารสูง แนะนำทำอาหารเอง")
    if expenses["travel"] > 10000:
        advice.append("✈️ ค่าเที่ยวสูงเกินไป ควรจำกัดงบ")

    if not advice:
        advice.append("✅ เยี่ยมมาก! การใช้จ่ายของคุณสมดุลและมีการออมเหมาะสม 👍")
    return " ".join(advice)

# ======================================================
# ⚙️ Simulation 12 เดือน
# ======================================================
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

# ======================================================
# 🚀 /simulate — บันทึกข้อมูลจำลอง
# ======================================================
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
    sim_result = simulate_with_simpy(income, expenses)

    total_exp = sum(expenses.values())
    balance = income - total_exp
    total_saving = balance * 12
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
        total_expense=total_exp,
        balance=balance,
        cumulative_saving=total_saving,
        created_at=datetime.now(),
        detail=advice
    )
    db.add(record)
    db.commit()

    return JSONResponse(content={
        "summary": {
            "name": user.name,
            "monthly_income": income,
            "monthly_expense": total_exp,
            "monthly_balance": balance,
            "total_saving_12m": total_saving,
            "expenses": expenses,
            "advice": advice
        },
        "simulation_result": sim_result
    })

# ======================================================
# 🧾 /history/{name} — ดึงประวัติผู้ใช้
# ======================================================
@app.get("/history/{name}")
def get_history(name: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.name == name).first()

    # ถ้ายังไม่มี user แต่มี record ให้สร้าง user ใหม่จาก record
    if not user:
        record = db.query(FinanceRecord).first()
        if record:
            new_user = User(name=name)
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            record.user_id = new_user.id
            db.commit()
            user = new_user
        else:
            raise HTTPException(status_code=404, detail="ไม่พบผู้ใช้")

    records = db.query(FinanceRecord).filter(FinanceRecord.user_id == user.id).all()
    if not records:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูลการจำลอง")

    return {
        "user": user.name,
        "records": [{
            "month": r.month,
            "income": r.income,
            "total_expense": r.total_expense,
            "balance": r.balance,
            "detail": r.detail,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S")
        } for r in records]
    }

# ======================================================
# 🧭 /history/summary — แสดงรายชื่อผู้ใช้ + คำแนะนำล่าสุด
# ======================================================
@app.get("/history/summary")
def get_summary(db: Session = Depends(get_db)):
    # 🔧 ซ่อมข้อมูล orphan record (ไม่มี user_id)
    orphan_records = db.query(FinanceRecord).filter(FinanceRecord.user_id == None).all()
    for rec in orphan_records:
        # ถ้าไม่มี user ให้สร้างจากชื่อ dummy
        dummy_user = User(name="ผู้ใช้ไม่ระบุ")
        db.add(dummy_user)
        db.commit()
        db.refresh(dummy_user)
        rec.user_id = dummy_user.id
        db.commit()

    users = db.query(User).all()
    user_names, details = [], []

    for u in users:
        last_record = (
            db.query(FinanceRecord)
            .filter(FinanceRecord.user_id == u.id)
            .order_by(FinanceRecord.created_at.desc())
            .first()
        )
        if last_record:
            user_names.append(u.name)
            details.append({
                "name": u.name,
                "latest_advice": last_record.detail or "ยังไม่มีคำแนะนำ"
            })

    if not user_names:
        raise HTTPException(status_code=404, detail="ยังไม่มีข้อมูลในระบบ")

    return {"users": user_names, "details": details}

# ======================================================
# 🌍 Root
# ======================================================
@app.get("/")
def root():
    return {"message": "💰 Finance Simulation API is running successfully!"}

# ======================================================
# 🧩 Debug Route
# ======================================================
@app.on_event("startup")
async def show_routes():
    print("\n📍 Loaded Routes:")
    for route in app.routes:
        if hasattr(route, "path"):
            print(f"➡️ {route.path}")
    print("===================================\n")
