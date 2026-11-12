document.addEventListener("submit", (event) => {
  if (!event.target.matches("[data-logout]")) return;

  if (!window.confirm("از حساب خود خارج می‌شوید؟") ||
      !window.confirm("برای خروج، این تصمیم را دوباره تأیید کنید.")) {
    event.preventDefault();
  }
});
