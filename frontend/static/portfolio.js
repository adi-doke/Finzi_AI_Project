/* portfolio.js
   Responsibilities:
   - load finance data from localStorage.financeData (preferred) or fetch from /mcp/<phone>
   - render three charts using Chart.js:
     1) Asset Allocation (pie)
     2) Assets vs Liabilities (bar)
     3) Credit Score (horizontal bar)
   - show summary cards and allow manual refresh (fetch from backend)
   - gracefully handle missing fields
*/

/* ---------- Utility helpers ---------- */
const currencyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0
});

function safeNumber(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

function getStoredFinance() {
  try {
    const raw = localStorage.getItem('financeData');
    if (!raw) return null;
    return JSON.parse(raw);
  } catch (e) {
    console.warn('Invalid financeData in localStorage', e);
    return null;
  }
}

/* ---------- Chart references ---------- */
let assetPieChart = null;
let assetsBarChart = null;
let creditBarChart = null;

/* ---------- DOM elements ---------- */
const totalAssetsEl = document.getElementById('totalAssets');
const totalLiabilitiesEl = document.getElementById('totalLiabilities');
const netWorthEl = document.getElementById('netWorth');
const creditScoreEl = document.getElementById('creditScore');
const rawDataEl = document.getElementById('rawData');
const msgEl = document.getElementById('message');
const lastUpdatedEl = document.getElementById('lastUpdated');

const refreshBtn = document.getElementById('refreshBtn');
const logoutBtn = document.getElementById('logoutBtn');
const portfolioLink = document.getElementById('portfolioLink');

/* ---------- Topbar ---------- */
(function setupTopbar() {
  function updateTopbar() {
    const phone = localStorage.getItem('userPhone');
    if (phone) {
      portfolioLink?.style && (portfolioLink.style.display = 'inline-block');
      logoutBtn?.style && (logoutBtn.style.display = 'inline-block');
    } else {
      portfolioLink?.style && (portfolioLink.style.display = 'none');
      logoutBtn?.style && (logoutBtn.style.display = 'none');
    }
  }

  logoutBtn?.addEventListener('click', () => {
    localStorage.removeItem('userPhone');
    localStorage.removeItem('financeData');
    window.location.href = '/login';
  });

  document.addEventListener('DOMContentLoaded', updateTopbar);
  window.addEventListener('storage', updateTopbar);
})();

/* ---------- Fetch finance data ---------- */
async function fetchFinanceFromServer() {
  msgEl.textContent = '';
  const phone = localStorage.getItem('userPhone');
  if (!phone) {
    msgEl.textContent = 'Not logged in. Please log in first.';
    setTimeout(() => (window.location.href = '/login'), 900);
    throw new Error('Not logged in');
  }

  try {
    const res = await fetch(`/mcp/${encodeURIComponent(phone)}`);
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    const finance = data.finance || data || {};
    localStorage.setItem('financeData', JSON.stringify(finance));
    localStorage.setItem('financeDataLastFetched', new Date().toISOString());
    return finance;
  } catch (err) {
    console.error('Failed to fetch finance:', err);
    msgEl.textContent = 'Failed to fetch finance data: ' + (err.message || '');
    throw err;
  }
}

/* ---------- Charts ---------- */
function destroyCharts() {
  assetPieChart?.destroy();
  assetsBarChart?.destroy();
  creditBarChart?.destroy();
}

function renderCharts(finance) {
  destroyCharts();

  const bank = safeNumber(finance.bank_balance ?? 0);
  const mutual = safeNumber(finance.mutual_funds ?? 0);
  const stocks = safeNumber(finance.stocks ?? 0);
  const loan = safeNumber(finance.loan ?? 0);
  const credit = safeNumber(finance.credit_score ?? 0);

  const assetsTotal = bank + mutual + stocks;
  const liabilitiesTotal = loan;
  const netWorth = assetsTotal - liabilitiesTotal;

  totalAssetsEl.textContent = currencyFormatter.format(assetsTotal);
  totalLiabilitiesEl.textContent = currencyFormatter.format(liabilitiesTotal);
  netWorthEl.textContent = currencyFormatter.format(netWorth);
  creditScoreEl.textContent = credit ? credit.toString() : '—';

  // ❌ Removed raw JSON debug display
  if (rawDataEl) rawDataEl.innerHTML = '';

  // Asset Allocation Pie
  const pieCtx = document.getElementById('assetPie').getContext('2d');
  const pieLabels = [];
  const pieData = [];
  if (bank > 0) { pieLabels.push('Bank'); pieData.push(bank); }
  if (mutual > 0) { pieLabels.push('Mutual Funds'); pieData.push(mutual); }
  if (stocks > 0) { pieLabels.push('Stocks'); pieData.push(stocks); }
  if (pieData.length === 0) { pieLabels.push('No Data'); pieData.push(1); }

  assetPieChart = new Chart(pieCtx, {
    type: 'pie',
    data: {
      labels: pieLabels,
      datasets: [{
        data: pieData,
        backgroundColor: [
          'rgba(54, 162, 235, 0.8)',
          'rgba(255, 206, 86, 0.85)',
          'rgba(255, 99, 132, 0.85)',
        ],
        borderWidth: 0
      }]
    },
    options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
  });

  // Assets vs Liabilities Bar
  const barCtx = document.getElementById('assetsBar').getContext('2d');
  assetsBarChart = new Chart(barCtx, {
    type: 'bar',
    data: {
      labels: ['Assets', 'Liabilities'],
      datasets: [{
        label: 'Amount (INR)',
        data: [assetsTotal, liabilitiesTotal],
        backgroundColor: [
          'rgba(54, 162, 235, 0.85)',
          'rgba(255, 159, 64, 0.85)'
        ]
      }]
    },
    options: {
      responsive: true,
      scales: {
        y: { beginAtZero: true, ticks: { callback: v => (v >= 1000 ? v / 1000 + 'k' : v) } }
      },
      plugins: { legend: { display: false } }
    }
  });

  // Credit Score Horizontal Bar
  const creditCtx = document.getElementById('creditBar').getContext('2d');
  const creditMax = 900;
  creditBarChart = new Chart(creditCtx, {
    type: 'bar',
    data: {
      labels: ['Credit Score'],
      datasets: [{
        label: 'Score',
        data: [credit],
        backgroundColor: ['rgba(75, 192, 192, 0.9)'],
      }, {
        label: 'Max',
        data: [creditMax - credit],
        backgroundColor: ['rgba(0,0,0,0.06)'],
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      scales: {
        x: { stacked: true, max: creditMax, ticks: { stepSize: 100 } },
        y: { stacked: true }
      },
      plugins: { legend: { display: false } }
    }
  });

  // Allocation note
  const allocationNote = document.getElementById('allocationNote');
  if (allocationNote)
    allocationNote.textContent = `Showing top holdings. Total assets: ${currencyFormatter.format(assetsTotal)}.`;

  const lastFetched = localStorage.getItem('financeDataLastFetched');
  if (lastFetched)
    lastUpdatedEl.textContent = `Last updated: ${new Date(lastFetched).toLocaleString()}`;
  else
    lastUpdatedEl.textContent = '';
}

/* ---------- Init ---------- */
async function initPortfolio() {
  msgEl.textContent = '';
  try {
    let finance = getStoredFinance();
    if (!finance) finance = await fetchFinanceFromServer();
    renderCharts(finance);
  } catch (err) {
    console.warn('initPortfolio:', err);
  }
}

refreshBtn?.addEventListener('click', async () => {
  refreshBtn.disabled = true;
  refreshBtn.textContent = 'Refreshing...';
  try {
    const finance = await fetchFinanceFromServer();
    renderCharts(finance);
  } finally {
    refreshBtn.disabled = false;
    refreshBtn.textContent = 'Refresh';
  }
});

document.addEventListener('DOMContentLoaded', initPortfolio);
