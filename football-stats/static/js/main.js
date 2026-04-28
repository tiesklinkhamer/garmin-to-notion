// ── Tab switching ─────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const tabBar = document.getElementById("playerTabBar");
  if (tabBar) {
    tabBar.addEventListener("click", (e) => {
      const btn = e.target.closest(".tab-btn");
      if (!btn) return;

      // Deactivate all
      tabBar.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach(p => (p.style.display = "none"));

      // Activate clicked
      btn.classList.add("active");
      const panel = document.getElementById("tab-" + btn.dataset.tab);
      if (panel) panel.style.display = "";
    });
  }

  // ── Active nav link ──────────────────────────────────────
  const path = window.location.pathname;
  document.querySelectorAll(".nav-link").forEach(link => {
    const href = link.getAttribute("href")?.split("?")[0];
    if (href === path) link.classList.add("active");
  });
});
