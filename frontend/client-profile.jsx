import { createRoot } from "react-dom/client";

const sections = [
  { title: "جلسه‌های من", detail: "تقویم جلسه‌ها و وضعیت هر کدام.", href: "/profile/sessions/", icon: "event" },
  { title: "پرداخت‌های من", detail: "رسیدهای آفلاین رزرو.", href: "/profile/payments/", icon: "receipt_long" },
  { title: "اعلانات", detail: "آخرین خبر هر رویداد.", href: "/profile/notifications/", icon: "notifications" },
  { title: "پیدا کردن درمانگر", detail: "درمانگرهای تأییدشده و وقت آزاد.", href: "/therapists/", icon: "search" },
];

function ClientProfile({ name }) {
  return (
    <>
      <div className="welcome-card">
        <span className="welcome-card__sparkle material-symbols-outlined" aria-hidden="true">waving_hand</span>
        <div>
          <h2>سلام، {name}</h2>
          <p>این فضای شخصی شما در هم‌زبان است.</p>
        </div>
      </div>
      <div className="overview-grid">
        {sections.map((section) => (
          <a className="overview-card" key={section.title} href={section.href}>
            <span className="overview-card__icon material-symbols-outlined" aria-hidden="true">{section.icon}</span>
            <h3>{section.title}</h3>
            <p>{section.detail}</p>
          </a>
        ))}
      </div>
    </>
  );
}

const mount = document.getElementById("client-profile-app");
if (mount) {
  createRoot(mount).render(<ClientProfile name={mount.dataset.displayName || "دوست عزیز"} />);
}
