document.addEventListener("click", (event) => {
  const link = event.target.closest("[data-session-calendar] a");
  if (!link) return;
  event.preventDefault();
  loadCalendar(link.href, true);
});

window.addEventListener("popstate", () => {
  if (document.querySelector("[data-session-calendar]")) loadCalendar(window.location.href, false);
});

async function loadCalendar(url, push) {
  const root = document.querySelector("[data-session-calendar]");
  if (!root || root.getAttribute("aria-busy") === "true") return;
  root.setAttribute("aria-busy", "true");
  try {
    const response = await fetch(url, {
      headers: { "X-Calendar": "1" },
      credentials: "same-origin",
    });
    if (response.redirected) {
      window.location.assign(response.url);
      return;
    }
    if (!response.ok) throw new Error(String(response.status));
    root.outerHTML = await response.text();
    if (push) history.pushState({}, "", url);
  } catch (_error) {
    const current = document.querySelector("[data-session-calendar]");
    if (!current) return;
    current.removeAttribute("aria-busy");
    let note = current.querySelector("[data-calendar-error]");
    if (!note) {
      note = document.createElement("p");
      note.className = "form-error";
      note.setAttribute("role", "alert");
      note.dataset.calendarError = "";
      current.prepend(note);
    }
    note.textContent = "ماه عوض نشد. اتصال را بررسی کنید و دوباره تلاش کنید.";
  }
}
