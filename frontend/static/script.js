// script.js -- shared site utilities + minimal chat handling
// Place in your frontend static folder (e.g. frontend/static/script.js)

/* ---------- small utilities ---------- */
function getUserPhone() {
  return localStorage.getItem('userPhone') || null;
}
function setUserPhone(phone) {
  if (phone) localStorage.setItem('userPhone', phone);
  else localStorage.removeItem('userPhone');
}
function setFinanceData(finance) {
  if (finance) localStorage.setItem('financeData', JSON.stringify(finance));
  else localStorage.removeItem('financeData');
}
function getFinanceData() {
  try {
    const raw = localStorage.getItem('financeData');
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

/* ---------- Topbar helper (if pages include topbar) ---------- */
(function topbarSetup() {
  // This will safely run even if elements do not exist on the page
  document.addEventListener('DOMContentLoaded', () => {
    const portfolioLink = document.getElementById('portfolioLink');
    const logoutBtn = document.getElementById('logoutBtn');

    function updateTopbar() {
      const phone = getUserPhone();
      if (portfolioLink) portfolioLink.style.display = phone ? 'inline-block' : 'none';
      if (logoutBtn) logoutBtn.style.display = phone ? 'inline-block' : 'none';
    }

    if (logoutBtn) {
      logoutBtn.addEventListener('click', () => {
        setUserPhone(null);
        setFinanceData(null);
        window.location.href = '/login';
      });
    }

    updateTopbar();
    window.addEventListener('storage', updateTopbar);
  });
})();

/* ---------- Minimal chat UI logic (pages that have chatContainer) ---------- */
(function chatSetup() {
  document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('chatContainer');
    if (!chatContainer) return; // nothing to do on non-chat pages

    // create a simple chat UI if one doesn't exist
    // Expectation: chatContainer will be present; create input + messages area inside it
    chatContainer.innerHTML = `
      <div id="messages" style="min-height:300px;border:1px solid #eee;padding:12px;border-radius:8px;background:#fff;overflow:auto;"></div>
      <form id="chatForm" style="display:flex; gap:8px; margin-top:12px;">
        <input id="chatInput" type="text" placeholder="Ask something about your finance..." style="flex:1;padding:10px;border:1px solid #ccc;border-radius:6px;" />
        <button type="submit" style="padding:10px 12px;border-radius:6px;">Send</button>
      </form>
    `;

    const messagesEl = document.getElementById('messages');
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');

    function appendMessage(from, text) {
      const wrap = document.createElement('div');
      wrap.style.margin = '8px 0';
      if (from === 'user') {
        wrap.innerHTML = `<div style="text-align:right;"><small>You</small><div style="display:inline-block;background:#dff3ff;padding:8px;border-radius:8px;margin-top:4px;">${escapeHtml(text)}</div></div>`;
      } else {
        wrap.innerHTML = `<div><small>FinZi</small><div style="display:inline-block;background:#f2f2f2;padding:8px;border-radius:8px;margin-top:4px;">${escapeHtml(text)}</div></div>`;
      }
      messagesEl.appendChild(wrap);
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    async function sendMessage(msg) {
      const phone = getUserPhone();
      appendMessage('user', msg);

      try {
        const res = await fetch('/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ phone, message: msg })
        });
        if (!res.ok) {
          const text = await res.text();
          appendMessage('bot', 'Server error: ' + text);
          return;
        }
        const data = await res.json();
        appendMessage('bot', data.reply || 'No reply');
      } catch (err) {
        appendMessage('bot', 'Network error: ' + (err.message || err));
      }
    }

    chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const v = chatInput.value && chatInput.value.trim();
      if (!v) return;
      sendMessage(v);
      chatInput.value = '';
    });

    // small helper to escape HTML
    function escapeHtml(str) {
      if (!str) return '';
      return str.replace(/[&<>"']/g, function (m) {
        return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[m];
      });
    }

    // Welcome message (optionally show finance summary)
    const finance = getFinanceData();
    if (finance) {
      appendMessage('bot', 'Welcome back! I can answer questions about your bank balance, mutual funds, stocks, loans and credit score. Try: "what is my balance?"');
    } else {
      appendMessage('bot', 'Welcome! Log in to ask questions about your portfolio.');
    }
  });
})();
