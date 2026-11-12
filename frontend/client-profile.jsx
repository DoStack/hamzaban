import { createRoot } from "react-dom/client";

const sections = [
  { title: "جلسه‌های من", detail: "جلسه‌های پیش‌رو و گذشته در این بخش نمایش داده می‌شوند.", icon: "◷" },
  { title: "پیدا کردن درمانگر", detail: "درمانگر و زمان مناسب خود را پیدا کنید.", icon: "⌕" },
  { title: "اطلاعات حساب", detail: "اطلاعات پروفایل خود را مدیریت کنید.", icon: "◎" },
];

function ClientProfile({ name }) {
  return (
    <>
      <div className="welcome-card">
        <span className="welcome-card__sparkle" aria-hidden="true">✦</span>
        <div>
          <h2>سلام، {name}</h2>
          <p>این فضای شخصی شما در هم‌زبان است.</p>
        </div>
      </div>
      <div className="overview-grid">
        {sections.map((section) => (
          <article className="overview-card" key={section.title}>
            <span className="overview-card__icon" aria-hidden="true">{section.icon}</span>
            <h3>{section.title}</h3>
            <p>{section.detail}</p>
            <span className="coming-soon">به‌زودی</span>
          </article>
        ))}
      </div>
    </>
  );
}

const mount = document.getElementById("client-profile-app");
if (mount) {
  createRoot(mount).render(<ClientProfile name={mount.dataset.displayName || "دوست عزیز"} />);
}
