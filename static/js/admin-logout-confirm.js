document.addEventListener("submit", (event) => {
  if (!event.target.matches("#logout-form")) return;

  if (!window.confirm("از پنل مدیریت خارج می‌شوید؟") ||
      !window.confirm("برای خروج، این تصمیم را دوباره تأیید کنید.")) {
    event.preventDefault();
  }
});
