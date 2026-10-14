import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import Chart from "chart.js/auto";
import "./styles.css";
import { cleanPhoneDigits, ensureAuth, formatCurrency, getJson, logout, postJson, streamPost } from "./api.js";

const navItems = [
  ["/", "Home", "fa-house"],
  ["/chat_page", "Chat", "fa-comments"],
  ["/insights", "Insights", "fa-lightbulb"],
  ["/portfolio", "My Portfolio", "fa-chart-pie"],
];

function Icon({ name }) {
  return <i className={`fas ${name}`} />;
}

function Topbar({ title = "FinZi", icon = "fa-chart-line", auth = true, children }) {
  return (
    <nav className="topbar">
      <a className="brand" href="/"><Icon name={icon} /> {title}</a>
      <div className="controls">
        {children || (auth ? <AppNav /> : null)}
      </div>
    </nav>
  );
}

function AppNav() {
  return (
    <>
      {navItems.map(([href, label, icon]) => (
        <a key={href} className="button" href={href}><Icon name={icon} /> {label}</a>
      ))}
      <ProfileMenu />
    </>
  );
}

function ProfileMenu() {
  const [open, setOpen] = useState(false);
  const [user, setUser] = useState(null);
  useEffect(() => { getJson("/api/auth/me").then((p) => setUser(p.user || null)).catch(() => {}); }, []);
  return (
    <div className="finzi-profile-root">
      <button className="button" type="button" onClick={() => setOpen(!open)}><Icon name="fa-user" /> Profile <Icon name="fa-chevron-down" /></button>
      {open && (
        <div className="finzi-profile-menu">
          <h3 style={{ margin: "0 0 8px" }}>{user?.name || "FinZi User"}</h3>
          <p style={{ margin: "0 0 12px", color: "var(--gray-600)" }}>Mobile: {user?.phone || "Not available"}</p>
          <p style={{ margin: "0 0 12px", color: "var(--gray-600)" }}>Mail: {user?.email || "Not added"}</p>
          <button className="button finzi-profile-action" type="button" onClick={() => alert(`Personal information\n\nName: ${user?.name || "Not available"}\nMobile no.: ${user?.phone || "Not available"}\nMail: ${user?.email || "Not added"}`)}><Icon name="fa-id-card" /> Personal information</button>
          <button className="button finzi-profile-action danger" type="button" onClick={async () => { if (confirm("Delete your FinZi account? This removes your profile and data.")) { await postJson("/api/account/delete", {}); window.location.href = "/login"; } }}><Icon name="fa-trash-alt" /> Delete account</button>
          <button className="button finzi-profile-action danger" type="button" onClick={logout}><Icon name="fa-right-from-bracket" /> Logout</button>
        </div>
      )}
    </div>
  );
}

function useAuthUser() {
  const [user, setUser] = useState(null);
  useEffect(() => { ensureAuth().then(setUser); }, []);
  return user;
}

function Landing() {
  return (
    <>
      <Topbar auth={false}>
        <a className="button secondary" href="/register">Sign up</a>
        <a className="button primary" href="/login"><Icon name="fa-lock" /> Sign in</a>
      </Topbar>
      <main className="container">
        <section className="home-hero">
          <div className="hero-main">
            <p className="eyebrow"><Icon name="fa-sparkles" /> Personal finance made calmer</p>
            <h1>Keep tabs on your money in one place.</h1>
            <p>FinZi brings spending insights, portfolio tracking, and AI-powered guidance into one simple dashboard so you can understand where your money goes without the spreadsheet headache.</p>
            <div className="hero-actions">
              <a className="button primary" href="/register"><Icon name="fa-arrow-right" /> Get started</a>
              <a className="button" href="/login">Sign in</a>
            </div>
          </div>
          <aside className="panel">
            <p className="eyebrow">FinZi dashboard</p>
            <div className="profile-grid">
              {["Net worth $189,334", "Cash and cards $42,120", "Investments $96,384"].map((item) => <div className="metric" key={item}><span>{item.split(" ").slice(0, -1).join(" ")}</span><strong>{item.split(" ").at(-1)}</strong></div>)}
            </div>
          </aside>
        </section>
        <FeatureGrid />
      </main>
    </>
  );
}

function FeatureGrid() {
  return (
    <section className="tab-grid">
      {[
        ["Track spending", "Review transactions, compare categories, and spot patterns before they become problems.", "fa-wallet"],
        ["AI guidance", "Ask FinZi questions and get plain-language help for budgeting, tracking, and financial decisions.", "fa-robot"],
      ].map(([title, text, icon]) => (
        <article className="card" key={title}>
          <div className="tab-icon"><Icon name={icon} /></div>
          <h3>{title}</h3>
          <p>{text}</p>
        </article>
      ))}
    </section>
  );
}

function Login() {
  const [show, setShow] = useState(false);
  const [msg, setMsg] = useState(null);
  const [loading, setLoading] = useState(false);
  async function submit(event) {
    event.preventDefault();
    setLoading(true); setMsg(null);
    const form = new FormData(event.currentTarget);
    try {
      const data = await postJson(`/login${window.location.search || ""}`, {
        phone: cleanPhoneDigits(form.get("phone")),
        password: form.get("password"),
      });
      setMsg(["success", "Login successful! Redirecting..."]);
      setTimeout(() => { window.location.href = data.redirect || "/chat_page"; }, 700);
    } catch (error) {
      setMsg(["error", error.message || "Login failed. Please check your credentials."]);
    } finally { setLoading(false); }
  }
  return (
    <>
      <Topbar auth={false}><a className="button secondary" href="/">Home</a><a className="button primary" href="/register">Sign up</a></Topbar>
      <main className="form-page">
        <div className="login-container">
          <div className="login-header"><h1>Welcome Back</h1><p>Sign in to your FinZi account</p></div>
          <form className="login-form" onSubmit={submit}>
              <FormInput name="phone" label="Phone Number" icon="fa-phone" placeholder="Enter your phone number" />
              <FormInput name="password" label="Password" icon="fa-lock" type={show ? "text" : "password"} placeholder="Enter your password" after={<button type="button" className="password-toggle" onClick={() => setShow(!show)}><Icon name={show ? "fa-eye-slash" : "fa-eye"} /></button>} />
              <div className="form-options"><label><input type="checkbox" /> Remember me</label><a href="#" onClick={(e) => { e.preventDefault(); alert("Password reset functionality would be implemented here"); }}>Forgot password?</a></div>
              <button className="submit-btn" disabled={loading}><Icon name={loading ? "fa-spinner fa-spin" : "fa-sign-in-alt"} /> {loading ? "Signing In..." : "Sign In"}</button>
              {msg && <div className={`message-box ${msg[0]}`}><Icon name={msg[0] === "success" ? "fa-check-circle" : "fa-exclamation-circle"} /> {msg[1]}</div>}
              <p style={{ textAlign: "center" }}>Don't have an account? <a href="/register">Create account</a></p>
          </form>
        </div>
      </main>
    </>
  );
}

function Register() {
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [msg, setMsg] = useState(null);
  const strength = [password.length >= 8, /[a-z]/.test(password), /[A-Z]/.test(password), /\d/.test(password), /[^A-Za-z0-9]/.test(password)].filter(Boolean).length;
  const strengthClass = !password ? "" : strength <= 2 ? "strength-weak" : strength <= 4 ? "strength-medium" : "strength-strong";
  async function submit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(form.entries());
    payload.phone = cleanPhoneDigits(payload.phone);
    if (!payload.name || !payload.phone || !payload.email || !payload.password) return setMsg(["error", "Please fill all required fields."]);
    try {
      const data = await postJson("/register", payload);
      if (!data.success) throw new Error(data.message);
      setMsg(["success", "Registration successful - redirecting to login..."]);
      setTimeout(() => { window.location.href = "/login"; }, 1000);
    } catch (error) { setMsg(["error", error.message || "Registration failed. Please try again."]); }
  }
  return (
    <>
      <Topbar auth={false}><a className="button secondary" href="/">Home</a><a className="button primary" href="/login">Sign in</a></Topbar>
      <main className="form-page">
        <div className="register-container">
          <div className="register-header"><h1>Join FinZi</h1><p>Create your account to start managing your finances</p></div>
          <form className="register-form" onSubmit={submit}>
            <FormInput name="name" label="Full name" icon="fa-user" placeholder="Enter your full name" />
            <FormInput name="phone" label="Mobile number" icon="fa-phone" placeholder="Enter your mobile number" />
            <FormInput name="email" label="Email" icon="fa-envelope" type="email" placeholder="Enter your email address" />
            <div className="form-row"><label>Gender</label><div className="input-with-icon"><Icon name="fa-venus-mars" /><select name="gender"><option value="">Select Gender</option><option value="male">Male</option><option value="female">Female</option><option value="other">Other</option><option value="prefer-not-to-say">Prefer not to say</option></select></div></div>
            <FormInput name="password" label="Password" icon="fa-lock" type={show ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Create a strong password" after={<button type="button" className="password-toggle" onClick={() => setShow(!show)}><Icon name={show ? "fa-eye-slash" : "fa-eye"} /></button>} />
            <div className="password-strength"><span>{!password ? "Password strength" : strength <= 2 ? "Weak password" : strength <= 4 ? "Medium strength password" : "Strong password"}</span><div className="strength-bar"><div className={`strength-fill ${strengthClass}`} /></div></div>
            <button className="submit-btn"><Icon name="fa-user-plus" /> Create Account</button>
            {msg && <div className={`message-box ${msg[0]}`}><Icon name={msg[0] === "success" ? "fa-check-circle" : "fa-exclamation-circle"} /> {msg[1]}</div>}
            <p style={{ textAlign: "center" }}>Already have an account? <a href="/login">Sign in</a></p>
          </form>
        </div>
      </main>
    </>
  );
}

function FormInput({ label, icon, after, ...props }) {
  return <div className="form-row"><label>{label}</label><div className="input-with-icon"><Icon name={icon} /><input required {...props} />{after}</div></div>;
}

function Home() {
  const user = useAuthUser();
  const [finance, setFinance] = useState({});
  useEffect(() => { getJson("/api/profile").then((p) => setFinance(p.finance || {})).catch(() => {}); }, []);
  return (
    <>
      <Topbar />
      <main className="container">
        <section className="home-hero">
          <div className="hero-main">
            <p className="eyebrow">Financial command center</p>
            <h1>Welcome back, {user?.name || "there"}</h1>
            <p>Move from quick questions to deeper planning without losing context: chat with the assistant, review spending insights, and track assets with confidence.</p>
            <div className="hero-actions"><a className="button primary" href="/chat_page"><Icon name="fa-comments" /> Open Chat</a></div>
          </div>
          <aside className="panel"><p className="eyebrow">Snapshot</p><div className="profile-grid">
            <Metric label="Bank balance" value={formatCurrency(finance.bank_balance)} />
            <Metric label="Investments" value={formatCurrency((finance.mutual_funds || 0) + (finance.stocks || 0))} />
            <Metric label="Loan balance" value={formatCurrency(finance.loan)} />
            <Metric label="Credit score" value={finance.credit_score || "-"} />
          </div></aside>
        </section>
        <section className="tab-grid">{navItems.slice(1).map(([href, label, icon]) => <a className="tab-card" href={href} key={href}><div><div className="tab-icon"><Icon name={icon} /></div><h2>{label}</h2><p>Open your {label.toLowerCase()} workspace inside FinZi.</p></div><span>Open <Icon name="fa-arrow-right" /></span></a>)}</section>
      </main>
    </>
  );
}

function Metric({ label, value }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong></div>;
}

function Chat() {
  const user = useAuthUser();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const bottomRef = useRef(null);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);
  function newChat() { setInput(""); setMessages([]); }
  async function send() {
    const text = input.trim(); if (!text || isSending) return;
    const history = messages
      .filter((message) => message.content !== "FinZi is thinking...")
      .map((message) => ({ role: message.role === "bot" ? "assistant" : "user", content: message.content }));
    setMessages((m) => [...m, { role: "user", content: text }, { role: "bot", content: "FinZi is thinking..." }]);
    setInput(""); setIsSending(true);
    try {
      let current = "";
      await streamPost("/api/chat/stream", { message: text, history }, (_, collected) => {
        current = collected;
        setMessages((m) => [...m.slice(0, -1), { role: "bot", content: current }]);
      });
    } catch {
      const fallback = await postJson("/api/chat", { message: text, history });
      setMessages((m) => [...m.slice(0, -1), { role: "bot", content: fallback.reply || "No response available." }]);
    } finally { setIsSending(false); }
  }
  return (
    <>
      <Topbar title="FinZi" />
      <main className="chat-shell">
        <aside className="card chat-sidebar">
          <div className="chat-sidebar-header"><h3>Chat</h3><p>Ask a question about your finances.</p></div>
          <div className="chat-sidebar-body"><button className="button primary" disabled={isSending} onClick={newChat}><Icon name="fa-plus" /> New Chat</button></div>
        </aside>
        <section>
          <div className="card chat-session-banner"><strong>{messages.length ? "Conversation" : "New chat"}</strong></div>
          <div className="card chat-container">
            <div className="chat-messages">
              {!messages.length && <div className="chat-message bot">Hello {user?.name || "there"}! I'm your FinZi financial assistant. Ask me about spending, savings, budgets, or trends.</div>}
              {messages.map((m, i) => <div className={`chat-message ${m.role}`} key={i}><div style={{ whiteSpace: "pre-wrap" }}>{m.content}</div><div className="message-time">Just now</div></div>)}
              <div ref={bottomRef} />
            </div>
            <div className="chat-input-container"><div className="chat-input-wrapper"><textarea className="chat-input" disabled={isSending} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} placeholder="Type your question..." /><button className="send-button" disabled={isSending || !input.trim()} onClick={send}><Icon name="fa-paper-plane" /></button></div></div>
          </div>
        </section>
      </main>
    </>
  );
}

function ChartCanvas({ id, config, height = 300 }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!config || !ref.current) return;
    const chart = new Chart(ref.current, config);
    return () => chart.destroy();
  }, [config]);
  return <div className="chart-box" style={{ height }}><canvas ref={ref} id={id} /></div>;
}

function Insights() {
  useAuthUser();
  const [data, setData] = useState(null);
  const [ai, setAi] = useState(null);
  useEffect(() => { Promise.all([getJson("/api/insights/monthly_spending"), getJson("/api/insights/income_vs_expenses"), getJson("/api/insights/category_spending"), getJson("/api/insights/top_merchants?limit=10"), getJson("/api/insights/net_worth_trend")]).then(([ms, ie, cs, tm, nw]) => setData({ ms, ie, cs, tm, nw })); getJson("/api/insights/ai").then(setAi).catch(() => setAi({ summary: "The AI summary is temporarily unavailable.", insights: [] })); }, []);
  const charts = useMemo(() => data && [
    ["Monthly Spending", { type: "line", data: { labels: data.ms.months, datasets: [{ label: "Spent (INR)", data: data.ms.amounts, fill: true, tension: 0.3 }] }, options: { responsive: true, maintainAspectRatio: false } }],
    ["Income vs Expenses", { type: "line", data: { labels: data.ie.months, datasets: [{ label: "Income", data: data.ie.income, tension: 0.3 }, { label: "Expenses", data: data.ie.expenses, tension: 0.3 }] }, options: { responsive: true, maintainAspectRatio: false } }],
    ["Category Spending", { type: "bar", data: { labels: data.cs.categories, datasets: [{ label: "Spent by Category", data: data.cs.amounts }] }, options: { indexAxis: "y", responsive: true, maintainAspectRatio: false } }],
    ["Top Merchants", { type: "bar", data: { labels: data.tm.merchants, datasets: [{ label: "Top Merchants", data: data.tm.amounts }] }, options: { indexAxis: "y", responsive: true, maintainAspectRatio: false } }],
    ["Net Worth", { type: "line", data: { labels: data.nw.months, datasets: [{ label: "Net Worth (INR)", data: data.nw.net_worth, fill: true, tension: 0.3 }] }, options: { responsive: true, maintainAspectRatio: false } }],
  ], [data]);
  return <><Topbar title="FinZi Insights" /><main className="container"><h1>Insights</h1><section className="insights-grid">{charts ? charts.map(([title, config]) => <div className="card chart-card" key={title}><h3>{title}</h3><ChartCanvas config={config} /></div>) : <div className="card">Loading charts...</div>}<div className="card" style={{ gridColumn: "1 / -1" }}><h3>AI Financial Insights</h3><p>{ai?.summary || "Loading your personalized insights..."}</p><div className="tab-grid">{(ai?.insights || []).map((x) => <div className="card" key={x.title}><strong>{x.type}</strong><h4>{x.title}</h4><p>{x.detail}</p></div>)}</div></div></section></main></>;
}

function Portfolio() {
  useAuthUser();
  const [finance, setFinance] = useState(null);
  const load = () => getJson("/api/me/finance").then((d) => setFinance(d.finance || d));
  useEffect(load, []);
  const totalAssets = (finance?.bank_balance || 0) + (finance?.mutual_funds || 0) + (finance?.stocks || 0);
  const totalLiabilities = finance?.loan || 0;
  const creditPct = Math.max(0, Math.min(100, (((finance?.credit_score || 0) - 300) / 600) * 100));
  return <><Topbar title="FinZi" /><main className="container"><div className="hero"><h1><Icon name="fa-chart-bar" /> My Portfolio</h1><button className="button" onClick={load}><Icon name="fa-sync-alt" /> Refresh</button></div><section className="grid-cards">{[["Total Assets", totalAssets, "fa-wallet"], ["Total Liabilities", totalLiabilities, "fa-credit-card"], ["Net Worth", totalAssets - totalLiabilities, "fa-balance-scale"], ["Credit Score", finance?.credit_score || 0, "fa-star"]].map(([l, v, i]) => <div className="card" key={l}><h3><Icon name={i} /> {l}</h3><div className="stat-value">{l === "Credit Score" ? v : formatCurrency(v)}</div></div>)}</section><section className="charts"><div className="card chart-card"><h3>Asset Allocation</h3>{finance && <ChartCanvas config={{ type: "doughnut", data: { labels: ["Bank", "Mutual Funds", "Stocks"], datasets: [{ data: [finance.bank_balance, finance.mutual_funds, finance.stocks], backgroundColor: ["#3b82f6", "#10b981", "#f59e0b"] }] }, options: { plugins: { legend: { position: "bottom" } } } }} />}</div><div className="card chart-card"><h3>Assets vs Liabilities</h3>{finance && <ChartCanvas config={{ type: "bar", data: { labels: ["Assets", "Liabilities"], datasets: [{ data: [totalAssets, totalLiabilities], backgroundColor: ["rgba(59,130,246,0.7)", "rgba(245,158,11,0.7)"] }] }, options: { plugins: { legend: { display: false } } } }} />}</div><div className="card" style={{ gridColumn: "1 / -1" }}><h3>Credit Score</h3><div className="credit-score-bar"><div className="credit-score-fill" style={{ width: `${creditPct}%` }} /><div className="credit-score-marker" style={{ left: `${creditPct}%` }} /></div><div className="credit-score-labels"><span>300</span><span>600</span><span>900</span></div></div></section></main></>;
}

function Budget() {
  useAuthUser();
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("");
  const load = () => getJson("/api/budget/plan").then(setData);
  useEffect(load, []);
  const items = data?.category_progress || [];
  async function save(event) {
    event.preventDefault();
    const fd = new FormData(event.currentTarget);
    const category_budgets = {};
    for (const [key, value] of fd.entries()) if (key.startsWith("cat:")) category_budgets[key.slice(4)] = Number(value || 0);
    setStatus("Saving budget plan...");
    await postJson("/api/budget/plan", { monthly_income: Number(fd.get("monthly_income") || 0), savings_goal: Number(fd.get("savings_goal") || 0), notes: fd.get("notes") || "", category_budgets });
    setStatus("Budget plan saved successfully."); load();
  }
  const editable = data?.goal?.category_budgets || data?.suggested?.category_budgets || {};
  return <><Topbar title="FinZi Budget Planner" icon="fa-bullseye" /><main className="container"><section className="hero"><div><h1>Personal Budget Planner</h1><p>Set monthly savings targets, review suggested category budgets, and keep spending aligned with your current transaction patterns.</p></div></section><section className="grid-cards">{[["Monthly income", data?.goal?.monthly_income || data?.suggested?.monthly_income], ["Savings goal", data?.goal?.savings_goal || data?.suggested?.savings_goal], ["Current spend", data?.tracking?.current_spend], ["Remaining budget", data?.tracking?.remaining_budget]].map(([l, v]) => <div className="card" key={l}><div className="stat-label">{l}</div><div className="stat-value">{formatCurrency(v)}</div></div>)}</section><section className="layout"><div className="card"><h2>Budget vs spend</h2>{items.length ? <ChartCanvas config={{ type: "bar", data: { labels: items.map((i) => i.category), datasets: [{ label: "Spent", data: items.map((i) => i.spent), backgroundColor: "rgba(19,143,135,.72)" }, { label: "Budget", data: items.map((i) => i.budget), backgroundColor: "rgba(16,185,129,.55)" }] }, options: { responsive: true, maintainAspectRatio: false } }} /> : "Loading budget data..."}</div><div className="card"><h2>AI recommendation</h2><p style={{ whiteSpace: "pre-wrap" }}>{data?.ai_recommendation || "Loading your personalized budget recommendation..."}</p></div></section><section className="layout" style={{ marginTop: 18 }}><div className="card"><h2>Category budgets</h2><div className="budget-list">{items.map((item) => <div className="budget-row" key={item.category}><div className="budget-row-top"><span>{item.category}</span><span>{formatCurrency(item.spent)} / {formatCurrency(item.budget)}</span></div><div className="progress-track"><div className="progress-fill" style={{ width: `${Math.min((item.progress || 0) * 100, 100)}%` }} /></div></div>)}</div></div><div className="card"><h2>Update plan</h2><form onSubmit={save}><div className="field"><label>Monthly income</label><input name="monthly_income" type="number" defaultValue={data?.goal?.monthly_income || data?.suggested?.monthly_income || 0} /></div><div className="field"><label>Savings goal</label><input name="savings_goal" type="number" defaultValue={data?.goal?.savings_goal || data?.suggested?.savings_goal || 0} /></div><div className="field"><label>Notes</label><textarea name="notes" defaultValue={data?.goal?.notes || ""} /></div><div className="budget-input-grid">{Object.entries(editable).map(([cat, value]) => <div className="budget-input" key={cat}><label>{cat}</label><input name={`cat:${cat}`} type="number" defaultValue={Number(value || 0).toFixed(2)} /></div>)}</div><button className="button primary">Save Budget Plan</button><div className="status">{status}</div></form></div></section></main></>;
}

function ReceiptUpload() {
  useAuthUser();
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [status, setStatus] = useState("Select a receipt image to begin.");
  const [progress, setProgress] = useState("");
  const [raw, setRaw] = useState("OCR output will appear here.");
  const [receipt, setReceipt] = useState({});
  async function analyze() {
    if (!file) return setStatus("Please choose a receipt image first.");
    setStatus("Running OCR in your browser..."); setProgress("Loading OCR engine...");
    try {
      const result = await Tesseract.recognize(file, "eng", { logger: (m) => setProgress(`${m.status || ""}${typeof m.progress === "number" ? ` ${(m.progress * 100).toFixed(0)}%` : ""}`) });
      const text = result.data?.text?.trim();
      if (!text) throw new Error("No readable text was detected in the image.");
      setRaw(text); setStatus("OCR complete. Parsing receipt details...");
      const response = await postJson("/api/receipts/analyze", { raw_text: text, filename: file.name });
      setReceipt(response.receipt || {}); setStatus("Receipt parsed successfully."); setProgress("");
    } catch (error) { setStatus("Receipt analysis failed."); setRaw(error.message || String(error)); setProgress(""); }
  }
  return <><Topbar title="FinZi Receipt Upload" icon="fa-receipt" /><main className="container"><section className="hero"><div><h1>Upload a receipt and extract the data instantly</h1><p>Drop in a bill photo, let OCR read the text in your browser, and FinZi will infer the merchant, date, amount, and likely category automatically.</p></div><a className="cta" href="/monthly-report"><Icon name="fa-file-pdf" /> View Monthly Report</a></section><section className="layout"><div className="card"><h2>Receipt OCR</h2><div className="upload-box"><label>Choose receipt image</label><div className="upload-row"><input type="file" accept="image/*" onChange={(e) => { const f = e.target.files?.[0]; setFile(f || null); setPreview(f ? URL.createObjectURL(f) : ""); setStatus(f ? `Ready to analyze ${f.name}.` : "Select a receipt image to begin."); }} /><button className="button primary" onClick={analyze}><Icon name="fa-wand-magic-sparkles" /> Analyze Receipt</button></div><div className="status">{status}</div><div className="preview">{preview && <img src={preview} alt="Receipt preview" />}<div><div className="status">{progress}</div><button className="button" onClick={() => { setFile(null); setPreview(""); setRaw("OCR output will appear here."); setReceipt({}); setStatus("Select a receipt image to begin."); }}>Reset</button></div></div></div></div><div className="card"><h2>Extracted Details</h2><div className="result-grid">{[["Merchant", receipt.merchant || "-"], ["Amount", receipt.amount != null ? formatCurrency(receipt.amount) : "-"], ["Date", receipt.date || "-"], ["Category", receipt.category || "-"]].map(([l, v]) => <div className="result-item" key={l}><div className="stat-label">{l}</div><strong>{v}</strong></div>)}</div><div className="raw-text">{raw}</div></div></section></main></>;
}

function MonthlyReport() {
  useAuthUser();
  const [report, setReport] = useState(null);
  useEffect(() => { getJson("/api/reports/monthly").then(setReport).catch(() => {}); }, []);
  const summary = report?.summary || {};
  return <><Topbar title="FinZi Monthly Report" icon="fa-file-pdf" /><main className="container"><section className="hero"><div><h1>Download a clean monthly finance report</h1><p>This report summarizes your income, expenses, savings, budget status, and AI insights into one downloadable PDF.</p></div><a className="cta" href="/api/reports/monthly.pdf"><Icon name="fa-download" /> Download PDF</a></section><section className="layout four">{[["Income", summary.income], ["Expenses", summary.expenses], ["Savings", summary.savings], ["Net Worth", summary.net_worth]].map(([l, v]) => <div className="card metric" key={l}><div><div className="label">{l}</div><div className="value">{formatCurrency(v)}</div></div></div>)}</section><section className="chart-grid"><div className="card"><h2>Income vs Expenses Trend</h2>{report && <ChartCanvas config={{ type: "line", data: { labels: (report.monthly_trends || []).map((x) => x.month), datasets: [{ label: "Income", data: (report.monthly_trends || []).map((x) => x.income || 0), borderColor: "#138f87", backgroundColor: "rgba(19,143,135,.12)", fill: true }, { label: "Expenses", data: (report.monthly_trends || []).map((x) => x.expenses || 0), borderColor: "#f59e0b", backgroundColor: "rgba(245,158,11,.1)", fill: true }] }, options: { responsive: true, maintainAspectRatio: false } }} />}</div><div className="card"><h2>Category Mix</h2>{report && <ChartCanvas config={{ type: "doughnut", data: { labels: (report.top_categories || []).map((x) => x.category || "Unknown"), datasets: [{ data: (report.top_categories || []).map((x) => x.spent || 0), backgroundColor: ["#138f87", "#12c4a8", "#f59e0b", "#3b82f6", "#8b5cf6"] }] }, options: { plugins: { legend: { position: "bottom" } } } }} />}</div></section><section className="grid"><div className="card"><h2>AI Summary</h2><p style={{ whiteSpace: "pre-wrap" }}>{report?.ai_summary || "Loading report..."}</p></div><div className="card"><h2>Budget Snapshot</h2><ReportList rows={[["Monthly income", report?.budget?.monthly_income], ["Savings goal", report?.budget?.savings_goal], ["Current spend", report?.budget?.current_spend], ["Remaining budget", report?.budget?.remaining_budget]]} /></div></section><section className="grid" style={{ marginTop: 16 }}><div className="card"><h2>Top Categories</h2><ReportList rows={(report?.top_categories || []).map((x) => [x.category || "Unknown", x.spent])} /></div><div className="card"><h2>Top Merchants</h2><ReportList rows={(report?.top_merchants || []).map((x) => [x.merchant || "Unknown", x.spent])} /></div></section></main></>;
}

function ReportList({ rows }) {
  return <div className="list">{rows.length ? rows.map(([label, value]) => <div className="list-item" key={label}><strong>{label}</strong>{formatCurrency(value || 0)}</div>) : <div className="list-item">No data available yet.</div>}</div>;
}

function App() {
  const path = window.location.pathname;
  if (path === "/login") return <Login />;
  if (path === "/register" || path === "/signup") return <Register />;
  if (path === "/landing") return <Landing />;
  if (path === "/chat_page") return <Chat />;
  if (path === "/insights") return <Insights />;
  if (path === "/portfolio") return <Portfolio />;
  return <Home />;
}

createRoot(document.getElementById("root")).render(<App />);
