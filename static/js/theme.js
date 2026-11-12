const toggle = document.querySelector("[data-theme-toggle]");

toggle?.addEventListener("click", () => {
  const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = nextTheme;
  try {
    localStorage.setItem("hamzaban-theme", nextTheme);
  } catch (_) {}
});
