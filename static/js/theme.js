const toggleSelector = "[data-theme-toggle]";

function setThemeLabel(theme) {
  const label = theme === "dark" ? "پوستهٔ روشن" : "پوستهٔ تیره";
  document.querySelectorAll(toggleSelector).forEach((toggle) => toggle.setAttribute("aria-label", label));
}

setThemeLabel(document.documentElement.dataset.theme === "dark" ? "dark" : "light");

document.addEventListener("click", (event) => {
  if (!event.target.closest(toggleSelector)) return;
  const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = nextTheme;
  setThemeLabel(nextTheme);
  try {
    localStorage.setItem("hamzaban-theme", nextTheme);
  } catch (_) {}
});
