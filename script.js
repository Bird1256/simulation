// ================================
// 💰 Simulation Frontend Script (Final Full Version with Graphs)
// ================================

const API_BASE = "http://127.0.0.1:8001";
const baht = n => Number(n || 0).toLocaleString("th-TH", { maximumFractionDigits: 2 });
const getNumber = id => parseFloat(document.getElementById(id).value) || 0;

document.getElementById("btnSim").addEventListener("click", simulate);
document.getElementById("btnHistory").addEventListener("click", showHistory);

// 🔐 ปิด reload ฟอร์มโดยอัตโนมัติ
window.addEventListener("submit", e => e.preventDefault(), true);

// ----------------------
// 🧮 ฟังก์ชันจำลอง
// ----------------------
async function simulate(e) {
  if (e) e.preventDefault();

  const name = document.getElementById("name").value.trim();
  const income = getNumber("income");
  const locationVal = document.getElementById("location").value.trim();

  // ✅ แปลงค่าจาก select เป็นข้อความภาษาไทย
  const locationMap = {
    home: "อยู่บ้าน",
    near: "ใกล้มหาวิทยาลัย",
    far: "ไกลมหาวิทยาลัย"
  };
  const location = locationMap[locationVal] || "ไม่ระบุ";

  const expenses = {
    house: getNumber("house"),
    car: getNumber("car"),
    food: getNumber("food"),
    saving: getNumber("saving"),
    travel: getNumber("travel")
  };

  if (!name) return alert("⚠️ กรุณากรอกชื่อผู้ใช้");
  if (income <= 0) return alert("⚠️ กรุณากรอกรายได้ต่อเดือน");
  if (location === "ไม่ระบุ") return alert("⚠️ กรุณาเลือกประเภทที่พัก");

  try {
    const res = await fetch(`${API_BASE}/simulate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, income, expenses, location })
    });

    if (!res.ok) throw new Error("API ตอบกลับผิดพลาด");
    const data = await res.json();

    renderResult(data, location);
  } catch (err) {
    console.error("❌ ERROR:", err);
    alert("❌ ไม่สามารถเชื่อมต่อ API ได้ กรุณาตรวจสอบการรัน main.py");
  }
}

// ----------------------
// 📊 แสดงผลจำลอง
// ----------------------
function renderResult(data, location) {
  const resultWrap = document.getElementById("resultWrap");
  const historyWrap = document.getElementById("historyWrap");

  resultWrap.classList.remove("hidden");
  historyWrap.classList.add("hidden");

  const s = data.summary;

  const locText = {
    "อยู่บ้าน": "🏠 อยู่บ้าน (ไม่มีค่าใช้จ่ายเพิ่มเติม)",
    "ใกล้มหาวิทยาลัย": "🏢 อยู่ใกล้มหาวิทยาลัย (+1,500 บาท ค่าน้ำค่าไฟ)",
    "ไกลมหาวิทยาลัย": "🚆 อยู่ไกลมหาวิทยาลัย (+1,500 บาท ค่าน้ำค่าไฟ)"
  }[location] || "ไม่ระบุ";

  document.getElementById("summary").innerHTML = `
    <p>👤 ชื่อผู้ใช้: <b>${s.name}</b></p>
    <p>📍 ที่พักอาศัย: ${locText}</p>
    <p>💵 รายได้ต่อเดือน: ${baht(s.monthly_income)} บาท</p>
    <p>🧾 รายจ่ายรวมต่อเดือน: ${baht(s.monthly_expense)} บาท</p>
    <p>💰 คงเหลือต่อเดือน: <b class="text-green-700">${baht(s.monthly_balance)}</b> บาท</p>
    <p>🏦 เงินออมรวม 12 เดือน: <b class="text-blue-700">${baht(s.total_saving_12m)}</b> บาท</p>
  `;

  // --------------------------
  // 🧾 ตารางแสดงรายจ่ายแต่ละหมวด
  // --------------------------
  const tbody1 = document.getElementById("breakdownTbody");
  let rows = Object.entries(s.expenses)
    .map(([key, val]) => `
      <tr>
        <td class="border px-3 py-2">${translateExpenseKey(key)}</td>
        <td class="border px-3 py-2 text-right">${baht(val)}</td>
      </tr>
    `)
    .join("");

  // ✅ เงื่อนไข: แสดงค่าน้ำค่าไฟเฉพาะเมื่อไม่ใช่ "อยู่บ้าน"
  if (location !== "อยู่บ้าน") {
    rows += `
      <tr>
        <td class="border px-3 py-2">ค่าน้ำค่าไฟ</td>
        <td class="border px-3 py-2 text-right">${baht(1500)}</td>
      </tr>
    `;
  }

  tbody1.innerHTML = rows;

  // --------------------------
  // 📆 ตารางสรุปผลแต่ละเดือน
  // --------------------------
  const tbody2 = document.getElementById("monthlyTbody");
  tbody2.innerHTML = data.simulation_result
    .map(m => `
      <tr>
        <td class="border px-3 py-2">${m.month}</td>
        <td class="border px-3 py-2 text-right">${baht(m.balance)}</td>
        <td class="border px-3 py-2 text-right">${baht(m.cumulative_saving)}</td>
      </tr>
    `)
    .join("");

  // 💡 ข้อเสนอแนะทางการเงิน
  document.getElementById("adviceBox").classList.remove("hidden");
  document.getElementById("adviceText").textContent = s.advice || "ไม่มีคำแนะนำเพิ่มเติม";

  // --------------------------
  // 💰 สร้างกราฟ รายได้ - รายจ่าย
  // --------------------------
  if (document.getElementById("incomeExpenseChart")) {
    const ctx = document.getElementById("incomeExpenseChart").getContext("2d");

    // ล้างกราฟเก่าก่อน (กันซ้อน)
    if (window.incomeExpenseChart) window.incomeExpenseChart.destroy();

    window.incomeExpenseChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: ["รายได้", "รายจ่ายรวม"],
        datasets: [{
          label: "จำนวนเงิน (บาท)",
          data: [s.monthly_income, s.monthly_expense],
          backgroundColor: ["#16a34a", "#ef4444"]
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          title: {
            display: true,
            text: "💰 รายได้ - รายจ่ายต่อเดือน",
            font: { size: 16 }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: val => val.toLocaleString("th-TH")
            },
            title: {
              display: true,
              text: "บาท"
            }
          }
        }
      }
    });
  }

  // เลื่อนลงมาแสดงผลลัพธ์
  resultWrap.scrollIntoView({ behavior: "smooth" });

  window.__lockSimulation = true;
}

// ----------------------
// 🧠 ดูประวัติย้อนหลัง
// ----------------------
async function showHistory(e) {
  if (e) e.preventDefault();

  const name = document.getElementById("name").value.trim();
  if (!name) return alert("⚠️ กรุณากรอกชื่อก่อนดูประวัติ");

  try {
    const res = await fetch(`${API_BASE}/history/${encodeURIComponent(name)}`);
    const data = await res.json();

    if (!data.records || data.records.length === 0)
      return alert("ยังไม่มีข้อมูลประวัติของผู้ใช้นี้");

    const resultWrap = document.getElementById("resultWrap");
    const historyWrap = document.getElementById("historyWrap");

    resultWrap.classList.add("hidden");
    historyWrap.classList.remove("hidden");

    const tbody = document.getElementById("historyTbody");
    tbody.innerHTML = data.records
      .map((r, i) => `
        <tr>
          <td class="border px-3 py-2 text-center">${i + 1}</td>
          <td class="border px-3 py-2 text-right">${baht(r.income)}</td>
          <td class="border px-3 py-2 text-right">${baht(r.total_expense)}</td>
          <td class="border px-3 py-2 text-right">${baht(r.balance)}</td>
          <td class="border px-3 py-2 text-center">${r.created_at}</td>
        </tr>
      `)
      .join("");

    window.__lockSimulation = false;
  } catch (err) {
    console.error(err);
    alert("❌ โหลดประวัติไม่สำเร็จ");
  }
}

// ----------------------
// 🔤 แปลชื่อหมวดรายจ่าย
// ----------------------
function translateExpenseKey(key) {
  const dict = {
    house: "บ้าน",
    car: "รถ / เดินทาง",
    food: "อาหาร",
    saving: "เงินออม",
    travel: "ท่องเที่ยว"
  };
  return dict[key] || key;
}

// ----------------------
// 🚫 ป้องกัน browser ล้างผลจำลอง
// ----------------------
window.addEventListener("beforeunload", e => {
  if (window.__lockSimulation) {
    e.preventDefault();
    e.returnValue = "";
  }
});
