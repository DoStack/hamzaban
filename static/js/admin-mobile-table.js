function addMobileTableLabels() {
  document.querySelectorAll("#result_list").forEach((table) => {
    const headers = Array.from(table.querySelectorAll("thead th")).map((header) => {
      const label = header.querySelector("a")?.textContent || header.textContent || "";
      return label.replace(/arrow_circle_down|arrow_circle_up|cancel/g, "").trim();
    });

    table.querySelectorAll("tbody tr").forEach((row) => {
      Array.from(row.cells).forEach((cell, index) => {
        if (headers[index]) cell.dataset.label = headers[index];
      });
    });
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", addMobileTableLabels, { once: true });
} else {
  addMobileTableLabels();
}
