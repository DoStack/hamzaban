function hourCells(root) {
  return [...root.querySelectorAll('input[name="cells"]')];
}

function syncHourGrid(root) {
  const cells = hourCells(root);
  const all = root.querySelector("[data-hour-all]");
  if (all) {
    const checked = cells.filter((input) => input.checked).length;
    all.checked = cells.length > 0 && checked === cells.length;
    all.indeterminate = checked > 0 && checked < cells.length;
  }
  root.querySelectorAll("[data-hour-day]").forEach((toggle) => {
    const dayCells = cells.filter((input) => input.dataset.day === toggle.dataset.hourDay);
    const checked = dayCells.filter((input) => input.checked).length;
    toggle.checked = dayCells.length > 0 && checked === dayCells.length;
    toggle.indeterminate = checked > 0 && checked < dayCells.length;
  });
}

document.addEventListener("change", (event) => {
  const root = event.target.closest("[data-hour-grid]");
  if (!root) return;
  if (event.target.matches("[data-hour-all]")) {
    hourCells(root).forEach((input) => {
      input.checked = event.target.checked;
    });
  } else if (event.target.matches("[data-hour-day]")) {
    const day = event.target.dataset.hourDay;
    hourCells(root).forEach((input) => {
      if (input.dataset.day === day) input.checked = event.target.checked;
    });
  }
  syncHourGrid(root);
});

function bootHourGrids() {
  document.querySelectorAll("[data-hour-grid]").forEach(syncHourGrid);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bootHourGrids, { once: true });
} else {
  bootHourGrids();
}
