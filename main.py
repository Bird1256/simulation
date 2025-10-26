# ================================================
# 💰 Finance Simulation Backend + 🤖 AI Advisor + 🏠 Location Fee (ตามที่อยู่)
# ================================================

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import sqlite3, json, warnings
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.exceptions import ConvergenceWarning

warnings.filterwarnings("ignore", category=ConvergenceWarning)

app = FastAPI(
    title="Student Financial Simulation API (AI Advisor + Location Fee)",
    description="จำลองการเงินนักศึกษา + วิเคราะห์พฤติกรรมการใช้เงินด้วย AI + ค่าที่พักคำนวณตามระยะทางจากมหาวิทยาลัย",
    version="2.3"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# 📦 Model สำหรับข้อมูลขาเข้า
# -----------------------------
class SimulationInput(BaseModel):
    name: str
    income: float
    expenses: dict
    location: str

# -----------------------------
# 🗃️ ตั้งค่า Database
# -----------------------------
DB_PATH = "finance.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS simulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            income REAL,
            total_expense REAL,
            balance REAL,
            expenses_json TEXT,
            created_at TEXT
        )
    """)
    cols = [r[1] for r in c.execute("PRAGMA table_info(simulations);").fetchall()]
    if "expenses_json" not in cols:
        c.execute("ALTER TABLE simulations ADD COLUMN expenses_json TEXT;")
    conn.commit()
    conn.close()

init_db()

# -----------------------------
# 🧠 ตัวช่วยของ AI Advisor
# -----------------------------
EXP_KEYS = ["house", "car", "food", "saving", "travel"]

def _safe_num(x):
    try:
        return float(x) if x is not None else 0.0
    except:
        return 0.0

def fetch_history_df():
    conn = sqlite3.connect(DB_PATH)
    rows = pd.read_sql_query("SELECT name, income, total_expense, balance, expenses_json, created_at FROM simulations", conn)
    conn.close()
    if rows.empty:
        for k in EXP_KEYS: rows[k] = 0.0
        return rows
    def parse_exp(js):
        if not js: return {k: 0.0 for k in EXP_KEYS}
        try: d = json.loads(js)
        except: d = {}
        return {k: _safe_num(d.get(k, 0.0)) for k in EXP_KEYS}
    exp_df = rows["expenses_json"].apply(parse_exp).apply(pd.Series)
    rows = pd.concat([rows.drop(columns=["expenses_json"]), exp_df], axis=1)
    eps = 1e-9
    for k in EXP_KEYS:
        rows[f"ratio_{k}"] = rows[k] / (rows["income"] + eps)
    return rows

def rule_based_flags(income, expenses):
    tips = []
    inc = max(income, 0.0)
    eps = 1e-9
    ratios = {k: _safe_num(expenses.get(k, 0.0)) / (inc + eps) for k in EXP_KEYS}
    if ratios["food"] > 0.40: tips.append("🍜 ค่าอาหารเกิน 40% ของรายได้")
    if ratios["car"] > 0.20: tips.append("🚌 ค่าเดินทางเกิน 20% ของรายได้")
    if ratios["house"] > 0.30: tips.append("🏠 ค่าที่พักเกิน 30% ของรายได้")
    if ratios["saving"] < 0.10: tips.append("💵 เงินออมต่ำกว่า 10% ของรายได้")
    if ratios["travel"] > 0.15: tips.append("✈️ ท่องเที่ยวเกิน 15% ของรายได้")
    total_exp = sum(_safe_num(expenses.get(k, 0.0)) for k in EXP_KEYS)
    if total_exp > income: tips.append("⚠️ รายจ่ายมากกว่ารายได้")
    return tips

def kmeans_advisor(current_vector, history_df, k=3):
    ratio_cols = [f"ratio_{k}" for k in EXP_KEYS]
    df = history_df.copy()
    df = df[df["income"] > 0]
    if df.shape[0] < 8:
        return {"enabled": False, "peer_tips": ["ข้อมูลย้อนหลังน้อยเกินไป"]}
    X = df[ratio_cols].fillna(0.0).to_numpy()
    k = max(2, min(k, X.shape[0] // 2))
    km = KMeans(n_clusters=k, n_init=10, random_state=42)
    km.fit(X)
    cur = np.array(current_vector).reshape(1, -1)
    label = int(km.predict(cur)[0])
    df["cluster"] = km.labels_
    peer = df[df["cluster"] == label]
    med = peer[ratio_cols].median().to_dict()
    peer_tips = []
    for i, key in enumerate(EXP_KEYS):
        cur_ratio = float(current_vector[i])
        peer_med = float(med.get(f"ratio_{key}", 0.0))
        if cur_ratio - peer_med > 0.10:
            peer_tips.append(f"📌 หมวด {key} สูงกว่าค่าเฉลี่ยเพื่อน")
    return {"enabled": True, "peer_tips": peer_tips or ["ใกล้เคียงเพื่อนแล้ว 👍"]}

def build_advisor(income, expenses):
    rb = rule_based_flags(income, expenses)
    hist = fetch_history_df()
    eps = 1e-9
    ratios_vec = [_safe_num(expenses.get(k, 0.0)) / (income + eps) for k in EXP_KEYS]
    km_res = kmeans_advisor(ratios_vec, hist)
    tips = rb + km_res.get("peer_tips", [])
    return " • ".join(tips) if tips else "การใช้จ่ายอยู่ในเกณฑ์เหมาะสม 👍"

# -----------------------------
# 📊 ฟังก์ชันจำลอง
# -----------------------------
@app.post("/simulate")
async def simulate(data: SimulationInput):
    income = data.income
    expenses = {k: _safe_num(data.expenses.get(k, 0.0)) for k in EXP_KEYS}
    location = data.location.strip()

    # ✅ เงื่อนไขค่าที่พักตามประเภทที่อยู่
    if location == "อยู่บ้าน":
        location_factor = 0
    elif location in ["ใกล้มหาวิทยาลัย", "ไกลมหาวิทยาลัย"]:
        location_factor = 1500
    else:
        location_factor = 0  # กันพลาด

    total_expense = sum(expenses.values()) + location_factor
    balance = income - total_expense
    total_saving_12m = balance * 12 if balance > 0 else 0

    advice = build_advisor(income, expenses)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO simulations (name, income, total_expense, balance, expenses_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (data.name, income, total_expense, balance, json.dumps(expenses, ensure_ascii=False),
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

    months = []
    cumulative = 0
    for i in range(1, 13):
        cumulative += balance
        months.append({
            "month": f"เดือน {i}",
            "balance": balance,
            "cumulative_saving": max(cumulative, 0)
        })

    return {
        "summary": {
            "name": data.name,
            "location": location,
            "monthly_income": income,
            "monthly_expense": total_expense,
            "monthly_balance": balance,
            "total_saving_12m": total_saving_12m,
            "expenses": expenses,
            "advice": advice
        },
        "simulation_result": months
    }

# -----------------------------
# 🧾 ประวัติย้อนหลัง
# -----------------------------
@app.get("/history/{name}")
async def get_history(name: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT income, total_expense, balance, created_at FROM simulations WHERE name=? ORDER BY id DESC", (name,))
    rows = c.fetchall()
    conn.close()
    records = [
        {"income": row[0], "total_expense": row[1], "balance": row[2], "created_at": row[3]}
        for row in rows
    ]
    return {"records": records}

@app.get("/")
def root():
    return {"message": "🎓 Simulation API + AI Advisor + 🏠 Location Fee: อยู่บ้าน 0 บาท / ใกล้-ไกลมหาวิทยาลัย 1,500 บาท"}
