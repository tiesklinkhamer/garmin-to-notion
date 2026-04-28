// ── Live search dropdown ──────────────────────────────────────────────────────
(function () {
  const input    = document.getElementById("searchInput");
  const dropdown = document.getElementById("searchDropdown");
  if (!input || !dropdown) return;

  let timer, focusIdx = -1;

  function items() { return dropdown.querySelectorAll(".sd-item"); }

  function setFocus(idx) {
    items().forEach((el, i) => el.classList.toggle("focused", i === idx));
    focusIdx = idx;
  }

  function hide() { dropdown.style.display = "none"; focusIdx = -1; }

  function render(data) {
    const { players, teams } = data;
    if (!players.length && !teams.length) {
      dropdown.innerHTML = `<div class="sd-empty">No results found</div>`;
    } else {
      let html = "";
      if (players.length) {
        html += `<div class="sd-section">Players</div>`;
        players.forEach(p => {
          const sub = [p.team, p.nat, p.league].filter(Boolean).join(" · ");
          html += `
            <a href="/player/${p.id}" class="sd-item">
              <div class="sd-avatar">${p.name.split(" ").map(w => w[0]).slice(0, 2).join("")}</div>
              <div>
                <div class="sd-name">${p.name}</div>
                <div class="sd-sub">${sub}</div>
              </div>
              <div class="sd-goals">${p.goals} ⚽</div>
            </a>`;
        });
      }
      if (teams.length) {
        if (players.length) html += `<hr class="sd-divider">`;
        html += `<div class="sd-section">Teams</div>`;
        teams.forEach(t => {
          const img = t.crest
            ? `<img src="${t.crest}" class="sd-crest" onerror="this.style.display='none'">`
            : `<div class="sd-avatar">${t.name[0]}</div>`;
          html += `
            <a href="/team/${t.id}" class="sd-item">
              ${img}
              <div>
                <div class="sd-name">${t.name}</div>
                <div class="sd-sub">${t.league}</div>
              </div>
            </a>`;
        });
      }
      dropdown.innerHTML = html;
    }
    dropdown.style.display = "block";
    focusIdx = -1;
  }

  input.addEventListener("input", () => {
    const q = input.value.trim();
    clearTimeout(timer);
    if (q.length < 2) { hide(); return; }
    timer = setTimeout(async () => {
      try {
        const res  = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
        const data = await res.json();
        render(data);
      } catch (_) { hide(); }
    }, 280);
  });

  // Keyboard navigation
  input.addEventListener("keydown", (e) => {
    const list = items();
    if (!list.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setFocus(Math.min(focusIdx + 1, list.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setFocus(Math.max(focusIdx - 1, 0));
    } else if (e.key === "Enter" && focusIdx >= 0) {
      e.preventDefault();
      list[focusIdx].click();
    } else if (e.key === "Escape") {
      hide();
    }
  });

  // Close on outside click
  document.addEventListener("click", (e) => {
    if (!input.closest(".search-wrap").contains(e.target)) hide();
  });

  input.addEventListener("focus", () => {
    if (input.value.trim().length >= 2 && dropdown.innerHTML) {
      dropdown.style.display = "block";
    }
  });
})();


// ── Goals / Assists tab switching on home page ────────────────────────────────
(function () {
  const tabs       = document.querySelectorAll(".scorer-tab");
  const goalsList  = document.getElementById("scorerGoals");
  const assistList = document.getElementById("scorerAssists");
  if (!tabs.length || !goalsList || !assistList) return;

  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      const mode = tab.dataset.mode;
      goalsList.style.display  = mode === "goals"   ? "" : "none";
      assistList.style.display = mode === "assists" ? "" : "none";
    });
  });
})();


// ── Player page tab switching ─────────────────────────────────────────────────
(function () {
  const bar = document.getElementById("playerTabBar");
  if (!bar) return;
  bar.addEventListener("click", (e) => {
    const btn = e.target.closest(".tab-btn");
    if (!btn) return;
    bar.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => (p.style.display = "none"));
    btn.classList.add("active");
    const panel = document.getElementById("tab-" + btn.dataset.tab);
    if (panel) panel.style.display = "";
  });
})();


// ── Active nav link ───────────────────────────────────────────────────────────
(function () {
  const path = window.location.pathname;
  document.querySelectorAll(".nav-link").forEach(link => {
    if ((link.getAttribute("href") || "").split("?")[0] === path) {
      link.classList.add("active");
    }
  });
})();
