export async function request(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const text = await response.text();
    let message = text;
    try {
      message = JSON.parse(text).message || message;
    } catch {
      // Keep the raw response text when the server did not send JSON.
    }
    throw new Error(message || `Request failed (${response.status})`);
  }

  return response;
}

export async function getJson(path) {
  const response = await request(path, { method: "GET" });
  return response.json();
}

export async function postJson(path, body) {
  const response = await request(path, {
    method: "POST",
    body: JSON.stringify(body || {}),
  });
  return response.json();
}

export async function ensureAuth() {
  const payload = await getJson("/api/auth/me");
  if (!payload.authenticated) {
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.href = `/login?next=${next}`;
    return null;
  }
  return payload.user || null;
}

export async function logout() {
  try {
    await postJson("/api/auth/logout", {});
  } finally {
    localStorage.removeItem("userPhone");
    localStorage.removeItem("financeData");
    window.location.href = "/login";
  }
}

export async function streamPost(path, body, onChunk) {
  const response = await fetch(path, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      Accept: "text/plain",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body || {}),
  });

  if (!response.ok) {
    throw new Error((await response.text()) || `Request failed (${response.status})`);
  }

  const reader = response.body?.getReader();
  if (!reader) return "";

  const decoder = new TextDecoder();
  let collected = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });
    collected += chunk;
    onChunk?.(chunk, collected);
  }
  return collected;
}

export function formatCurrency(value) {
  const amount = Number(value || 0);
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Number.isFinite(amount) ? amount : 0);
}

export function cleanPhoneDigits(phone) {
  const digits = (phone || "").replace(/\D/g, "");
  return digits.length === 12 && digits.startsWith("91") ? digits.slice(2) : digits;
}
