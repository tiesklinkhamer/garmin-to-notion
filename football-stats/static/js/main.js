// Keep league selection in sync across page navigations
document.addEventListener("DOMContentLoaded", () => {
  const params = new URLSearchParams(window.location.search);
  const league = params.get("league");

  // Highlight active nav links
  document.querySelectorAll(".nav-link").forEach(link => {
    if (link.getAttribute("href") === window.location.pathname) {
      link.classList.add("active");
    }
  });

  // Propagate league param to nav links so switching pages keeps the league
  if (league) {
    document.querySelectorAll("a.nav-link[href='/'], a.nav-link[href='/teams']").forEach(link => {
      const url = new URL(link.href, window.location.origin);
      url.searchParams.set("league", league);
      link.href = url.pathname + url.search;
    });
  }
});
