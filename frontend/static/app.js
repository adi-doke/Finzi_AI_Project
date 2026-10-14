(function (window) {
  async function request(path, options = {}) {
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
      } catch (error) {
        // Keep the raw response text when the server did not send JSON.
      }
      throw new Error(message || `Request failed (${response.status})`);
    }

    return response;
  }

  async function getJson(path) {
    const response = await request(path, { method: "GET" });
    return response.json();
  }

  async function postJson(path, body) {
    const response = await request(path, {
      method: "POST",
      body: JSON.stringify(body || {}),
    });
    return response.json();
  }

  async function ensureAuth() {
    const payload = await getJson("/api/auth/me");
    if (!payload.authenticated) {
      const next = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.href = `/login?next=${next}`;
      return null;
    }
    return payload.user || null;
  }

  async function logout() {
    try {
      await postJson("/api/auth/logout", {});
    } catch (error) {
      console.warn("Logout request failed", error);
    } finally {
      localStorage.removeItem("userPhone");
      localStorage.removeItem("financeData");
      window.location.href = "/login";
    }
  }

  async function streamPost(path, body, onChunk) {
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
      const text = await response.text();
      throw new Error(text || `Request failed (${response.status})`);
    }

    if (!response.body) {
      return "";
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let collected = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }
      const chunk = decoder.decode(value, { stream: true });
      collected += chunk;
      if (onChunk) {
        onChunk(chunk, collected);
      }
    }

    return collected;
  }

  function formatCurrency(value) {
    const amount = Number(value || 0);
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(Number.isFinite(amount) ? amount : 0);
  }

  function escapeHtml(value) {
    return String(value || "").replace(/[&<>"']/g, (char) => {
      return {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      }[char];
    });
  }

  function bindLogoutButtons() {
    document.querySelectorAll("[data-finzi-logout]").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        logout();
      });
    });
  }

  function formatProfileValue(value, fallback) {
    const text = String(value || "").trim();
    return text || fallback;
  }

  const NAV_ITEMS = [
    { href: "/", label: "Home", icon: "fa-house" },
    { href: "/chat_page", label: "Chat", icon: "fa-comments" },
    { href: "/insights", label: "Insights", icon: "fa-lightbulb" },
    { href: "/portfolio", label: "My Portfolio", icon: "fa-chart-pie" },
  ];

  function hydrateAppNav() {
    const topbar = document.querySelector(".topbar");
    const controls = document.querySelector(".topbar .controls");
    if (!topbar || !controls) return;

    const brand = topbar.querySelector(".brand");
    if (brand) {
      brand.setAttribute("role", "link");
      brand.setAttribute("tabindex", "0");
      brand.style.cursor = "pointer";
      const goHome = () => {
        window.location.href = "/";
      };
      brand.addEventListener("click", goHome);
      brand.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          goHome();
        }
      });
    }

    const currentPath = window.location.pathname.replace(/\/$/, "") || "/";
    controls.innerHTML = NAV_ITEMS.map((item) => {
      const itemPath = item.href.replace(/\/$/, "") || "/";
      const active = itemPath === currentPath ? " active" : "";
      return `<a class="button finzi-nav-link${active}" href="${item.href}"><i class="fas ${item.icon}"></i> ${item.label}</a>`;
    }).join("");
  }

  async function hydrateProfileMenu() {
    const controls = document.querySelector(".topbar .controls");
    if (!controls) return;
    if (["/login", "/register", "/signup"].includes(window.location.pathname)) return;

    const payload = await getJson("/api/auth/me").catch(() => ({ authenticated: false }));
    if (!payload.authenticated) return;

    hydrateAppNav();

    const user = payload.user || {};
    const existingRoot = controls.querySelector(".finzi-profile-root");
    if (existingRoot) {
      existingRoot.remove();
    }

    const root = document.createElement("div");
    root.className = "finzi-profile-root";
    root.innerHTML = `
      <button type="button" class="finzi-profile-toggle" data-finzi-profile-toggle aria-expanded="false">
        <span class="finzi-profile-avatar"><i class="fas fa-user"></i></span>
        <span>Profile</span>
        <i class="fas fa-chevron-down" style="font-size:12px;"></i>
      </button>
      <div class="finzi-profile-menu" data-finzi-profile-menu hidden>
        <div class="finzi-profile-header">
          <div class="finzi-profile-avatar" style="width:42px;height:42px;"><i class="fas fa-user"></i></div>
          <p class="finzi-profile-name">${escapeHtml(user.name || "FinZi User")}</p>
          <p class="finzi-profile-subtitle">Manage your account and settings</p>
        </div>
        <div class="finzi-profile-body">
          <div>
            <div class="finzi-profile-section-title">Profile</div>
            <div class="finzi-profile-row">
              <div>
                <span class="finzi-profile-label">Name</span>
                <div class="finzi-profile-value">${escapeHtml(formatProfileValue(user.name, "Not available"))}</div>
              </div>
            </div>
            <div class="finzi-profile-row">
              <div>
                <span class="finzi-profile-label">Mobile no.</span>
                <div class="finzi-profile-value">${escapeHtml(formatProfileValue(user.phone, "Not available"))}</div>
              </div>
            </div>
            <div class="finzi-profile-row">
              <div>
                <span class="finzi-profile-label">Mail</span>
                <div class="finzi-profile-value">${escapeHtml(formatProfileValue(user.email, "Not added"))}</div>
              </div>
            </div>
          </div>
          <div>
            <div class="finzi-profile-section-title">Settings</div>
            <button type="button" class="finzi-profile-action" data-finzi-profile-action="personal">
              <i class="fas fa-id-card"></i>
              Personal information
            </button>
            <button type="button" class="finzi-profile-action danger" data-finzi-profile-action="delete">
              <i class="fas fa-trash-alt"></i>
              Delete account
            </button>
            <button type="button" class="finzi-profile-action danger" data-finzi-profile-action="logout">
              <i class="fas fa-right-from-bracket"></i>
              Logout
            </button>
          </div>
        </div>
      </div>
    `;

    controls.appendChild(root);

    const toggle = root.querySelector("[data-finzi-profile-toggle]");
    const menu = root.querySelector("[data-finzi-profile-menu]");
    const profileButtons = root.querySelectorAll("[data-finzi-profile-action]");

    function setOpen(open) {
      menu.hidden = !open;
      toggle.setAttribute("aria-expanded", String(open));
    }

    toggle.addEventListener("click", (event) => {
      event.preventDefault();
      setOpen(menu.hidden);
    });

    document.addEventListener("click", (event) => {
      if (!root.contains(event.target)) {
        setOpen(false);
      }
    });

    profileButtons.forEach((button) => {
      button.addEventListener("click", async () => {
        const action = button.getAttribute("data-finzi-profile-action");
        if (action === "personal") {
          alert(
            `Personal information\n\nName: ${formatProfileValue(user.name, "Not available")}\nMobile no.: ${formatProfileValue(user.phone, "Not available")}\nMail: ${formatProfileValue(user.email, "Not added")}`
          );
        } else if (action === "delete") {
          const ok = confirm("Delete your FinZi account? This removes your profile and data.");
          if (!ok) return;
          try {
            const response = await postJson("/api/account/delete", {});
            if (response && response.success) {
              window.location.href = "/login";
            } else {
              alert(response.message || "Could not delete the account right now.");
            }
          } catch (error) {
            alert(error.message || "Could not delete the account right now.");
          }
        } else if (action === "logout") {
          logout();
        }
      });
    });

    // Keep the old standalone logout button available in markup but out of the way.
    document.querySelectorAll("[data-finzi-logout]").forEach((button) => {
      button.style.display = "none";
    });
  }

  window.FinZi = {
    request,
    getJson,
    postJson,
    ensureAuth,
    logout,
    streamPost,
    formatCurrency,
    escapeHtml,
  };

  document.addEventListener("DOMContentLoaded", () => {
    bindLogoutButtons();
    hydrateProfileMenu().catch((error) => console.warn("Profile menu unavailable", error));
  });
})(window);
