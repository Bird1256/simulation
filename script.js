// ================================
// 💰 Simulation Frontend Script (Fixed Version)
// ================================

const API_BASE = "http://127.0.0.1:8001";
const baht = (n) => Number(n || 0).toLocaleString("th-TH", { maximumFractionDigits: 2 });
const getNumber = (id) => parseFloat(document.getElementById(id).value) || 0;

// ----------------------
// 🎯 Event Listeners
// ----------------------
document.getElementById("btnSim").addEventListener("click", simulate);
document.getElementById("btnHistory").addEventListener("click", showHistory);

// ----------------------
// 🧮 ฟังก์ชันจำลองการเงิน
// ----------------------
async function simulate(e) {
  if (e) e.preventDefault();

  const name = document.getElementById("name").value.trim();
  const income = getNumber("income");
  const expenses = {
    house: getNumber("house"),
    car: getNumber("car"),
    food: getNumber("food"),
    saving: getNumber("saving"),
    travel: getNumber("travel"),
  };

  if (!name) return alert("⚠️ กรุณากรอกชื่อผู้ใช้");
  if (income <= 0) return alert("⚠️ กรุณากรอกรายได้ต่อเดือน");

  try {
    const res = await fetch(`${API_BASE}/simulate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, income, expenses }),
    });

    if (!res.ok) throw new Error("API ตอบกลับผิดพลาด: " + res.status);
    const data = await res.json();
    console.log("✅ ได้ข้อมูลจำลองจาก API:", data);

    renderResult(data);
  } catch (err) {
    console.error("❌ Error:", err);
    alert("ไม่สามารถเชื่อมต่อ API ได้ กรุณาตรวจสอบการรัน main.py");
  }
}

// ----------------------
// 📊 แสดงผลจำลอง
// ----------------------
function renderResult(data) {
  const resultWrap = document.getElementById("resultWrap");
  const historyWrap = document.getElementById("historyWrap");

  // 🔒 ป้องกันการซ่อนผลลัพธ์โดยอัตโนมัติ
  window.__showingResult = true;

  // ซ่อนประวัติ และแสดงผลจำลอง
  historyWrap.classList.add("hidden");
  resultWrap.classList.remove("hidden");

  const s = data.summary;

  // ✅ แสดงข้อมูลสรุป
  document.getElementById("summary").innerHTML = `
    <p>ชื่อผู้ใช้: <b>${s.name}</b></p>
    <p>รายได้ต่อเดือน: ${baht(s.monthly_income)} บาท</p>
    <p>รายจ่ายรวมต่อเดือน: ${baht(s.monthly_expense)} บาท</p>
    <p>คงเหลือต่อเดือน: <b class="text-green-700">${baht(s.monthly_balance)}</b> บาท</p>
    <p>เงินออมรวม 12 เดือน: <b class="text-blue-700">${baht(s.total_saving_12m)}</b> บาท</p>
  `;

  // ✅ แสดงตารางรายจ่าย
  const tbody1 = document.getElementById("breakdownTbody");
  tbody1.innerHTML = Object.entries(s.expenses)
    .map(
      ([key, val]) => `
      <tr>
        <td class="border px-3 py-2">${translateExpenseKey(key)}</td>
        <td class="border px-3 py-2 text-right">${baht(val)}</td>
      </tr>`
    )
    .join("");

  // ✅ แสดงตารางจำลอง 12 เดือน
  const tbody2 = document.getElementById("monthlyTbody");
  tbody2.innerHTML = data.simulation_result
    .map(
      (m) => `
      <tr>
        <td class="border px-3 py-2">${m.month}</td>
        <td class="border px-3 py-2 text-right">${baht(m.balance)}</td>
        <td class="border px-3 py-2 text-right">${baht(m.cumulative_saving)}</td>
      </tr>`
    )
    .join("");

  // ✅ แสดงคำแนะนำ
  const adviceBox = document.getElementById("adviceBox");
  adviceBox.classList.remove("hidden");
  document.getElementById("adviceText").textContent = s.advice;

  // ✅ ป้องกันการ reload ฟอร์มอัตโนมัติ
  const form = document.querySelector("form");
  if (form) form.onsubmit = (ev) => ev.preventDefault();

  // ✅ Scroll ให้เห็นผลลัพธ์
  resultWrap.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ----------------------
// 🧠 ฟังก์ชันดูประวัติ
// ----------------------
async function showHistory(e) {
  if (e) e.preventDefault();

  const name = document.getElementById("name").value.trim();
  if (!name) return alert("⚠️ กรุณากรอกชื่อก่อนดูประวัติ");

  try {
    const res = await fetch(`${API_BASE}/history/${encodeURIComponent(name)}`);
    if (!res.ok) throw new Error("โหลดประวัติไม่สำเร็จ");
    const data = await res.json();

    if (!data.records || data.records.length === 0) {
      alert("ยังไม่มีข้อมูลประวัติของผู้ใช้นี้");
      return;
    }

    const resultWrap = document.getElementById("resultWrap");
    const historyWrap = document.getElementById("historyWrap");

    // ซ่อนผลจำลอง แสดงประวัติแทน
    resultWrap.classList.add("hidden");
    historyWrap.classList.remove("hidden");

    const tbody = document.getElementById("historyTbody");
    tbody.innerHTML = data.records
      .map(
        (r, i) => `
        <tr>
          <td class="border px-3 py-2 text-center">${i + 1}</td>
          <td class="border px-3 py-2 text-right">${baht(r.income)}</td>
          <td class="border px-3 py-2 text-right">${baht(r.total_expense)}</td>
          <td class="border px-3 py-2 text-right">${baht(r.balance)}</td>
          <td class="border px-3 py-2 text-center">${r.created_at}</td>
        </tr>`
      )
      .join("");

    historyWrap.scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    console.error(err);
    alert("❌ ไม่สามารถโหลดประวัติได้");
  }
}

// ----------------------
// 🔤 ฟังก์ชันแปลชื่อหมวดรายจ่าย
// ----------------------
function translateExpenseKey(key) {
  const dict = {
    house: "บ้าน",
    car: "รถ",
    food: "อาหาร",
    saving: "เงินออม",
    travel: "ท่องเที่ยว",
  };
  return dict[key] || key;
}

// ----------------------
// 🛡️ ป้องกันการรีเฟรชหรือซ่อนผลจำลอง
// ----------------------
window.addEventListener("beforeunload", (e) => {
  if (window.__showingResult) {
    e.preventDefault();
    e.returnValue = "";
  }
});
