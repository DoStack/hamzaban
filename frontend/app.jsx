import { createContext, useContext, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";

import { api, csrfToken } from "./api.js";

function go(href) {
  const url = new URL(href, window.location.origin);
  window.history.pushState({}, "", url.pathname + url.search + url.hash);
  window.dispatchEvent(new PopStateEvent("popstate"));
  window.scrollTo(0, 0);
}

function usePath() {
  const [path, setPath] = useState(() => window.location.pathname + window.location.search);
  useEffect(() => {
    const sync = () => setPath(window.location.pathname + window.location.search);
    const onClick = (event) => {
      const link = event.target.closest("a");
      if (!link || link.target || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const url = new URL(link.href, window.location.origin);
      if (url.origin !== window.location.origin) return;
      if (link.hasAttribute("data-reload")) return;
      if (/^\/(admin|api|receipts|licenses|static|sw\.js|manifest\.webmanifest)/.test(url.pathname)) return;
      if (url.pathname.startsWith("/therapist/calendar/")) return;
      event.preventDefault();
      go(url.pathname + url.search + url.hash);
    };
    window.addEventListener("popstate", sync);
    document.addEventListener("click", onClick);
    return () => {
      window.removeEventListener("popstate", sync);
      document.removeEventListener("click", onClick);
    };
  }, []);
  return path;
}

function useFetch(path) {
  const [tick, setTick] = useState(0);
  const [state, setState] = useState({ loading: true, error: "", data: null });
  useEffect(() => {
    let live = true;
    setState((current) => ({ ...current, loading: true, error: "" }));
    api(path)
      .then((data) => {
        if (live) setState({ loading: false, error: "", data });
      })
      .catch((error) => {
        if (live) setState({ loading: false, error: error.message, data: null });
      });
    return () => {
      live = false;
    };
  }, [path, tick]);
  return { ...state, reload: () => setTick((value) => value + 1) };
}

function Icon({ name }) {
  return <span className="material-symbols-outlined" aria-hidden="true">{name}</span>;
}

function Alert({ children }) {
  if (!children) return null;
  return <p className="form-error" role="alert">{children}</p>;
}

function Bone({ className = "" }) {
  return <span className={`bone ${className}`} />;
}

function CardSkeleton({ lines = 2 }) {
  return (
    <article className="record-card skeleton" aria-hidden="true">
      <div className="record-card__row">
        <Bone className="bone--title" />
        <Bone className="bone--chip" />
      </div>
      {Array.from({ length: lines }, (_, index) => <Bone className={index === lines - 1 ? "bone--line bone--short" : "bone--line"} key={index} />)}
    </article>
  );
}

function ListSkeleton({ count = 3, lines = 2 }) {
  return (
    <div className="panel-grid" role="status" aria-label="در حال بارگذاری">
      {Array.from({ length: count }, (_, index) => <CardSkeleton lines={lines} key={index} />)}
    </div>
  );
}

function DirectorySkeleton() {
  return (
    <div className="therapist-grid" role="status" aria-label="در حال بارگذاری">
      {Array.from({ length: 4 }, (_, index) => (
        <article className="therapist-card skeleton" key={index} aria-hidden="true">
          <Bone className="bone--avatar" />
          <div>
            <Bone className="bone--title" />
            <Bone className="bone--line" />
            <Bone className="bone--line bone--short" />
          </div>
          <Bone className="bone--button" />
        </article>
      ))}
    </div>
  );
}

function DetailSkeleton() {
  const boxes = [5, 1, 2, 2, 3, 3];
  return (
    <div className="therapist-layout" role="status" aria-label="در حال بارگذاری">
      <div className="therapist-detail">
        {boxes.map((lines, index) => (
          <section className="profile-box skeleton" key={index} aria-hidden="true">
            <Bone className="bone--title" />
            {index === 0 ? (
              <div className="therapist-detail__header">
                <Bone className="bone--avatar bone--avatar-lg" />
                <div>
                  <Bone className="bone--title" />
                  <Bone className="bone--line bone--short" />
                </div>
              </div>
            ) : null}
            {Array.from({ length: lines }, (_, line) => <Bone className="bone--line" key={line} />)}
          </section>
        ))}
      </div>
      <aside className="reserve-card skeleton" aria-hidden="true">
        <Bone className="bone--title" />
        <Bone className="bone--line" />
        <Bone className="bone--line" />
        <Bone className="bone--line bone--short" />
        <Bone className="bone--button" />
        <Bone className="bone--button" />
      </aside>
    </div>
  );
}

function StatSkeleton() {
  return (
    <dl className="stat-row" role="status" aria-label="در حال بارگذاری">
      {Array.from({ length: 4 }, (_, index) => (
        <div key={index} aria-hidden="true">
          <Bone className="bone--line bone--short" />
          <Bone className="bone--stat" />
        </div>
      ))}
    </dl>
  );
}

function FormSkeleton({ rows = 4 }) {
  return (
    <div className="stack-form" role="status" aria-label="در حال بارگذاری">
      {Array.from({ length: rows }, (_, index) => (
        <span className="skeleton-field" key={index}>
          <Bone className="bone--label" />
          <Bone className="bone--field" />
        </span>
      ))}
    </div>
  );
}

function FaqSkeleton() {
  return (
    <div role="status" aria-label="در حال بارگذاری">
      {Array.from({ length: 4 }, (_, index) => (
        <div className="faq-item skeleton" key={index} aria-hidden="true"><Bone className="bone--faq" /></div>
      ))}
    </div>
  );
}

function CalendarSkeleton() {
  return (
    <div role="status" aria-label="در حال بارگذاری">
      <div className="calendar-head">
        <Bone className="bone--button" />
        <Bone className="bone--title" />
        <Bone className="bone--button" />
      </div>
      <div className="calendar">
        {Array.from({ length: 7 }, (_, index) => <Bone className="bone--line" key={`name-${index}`} />)}
        {Array.from({ length: 35 }, (_, index) => (
          <div className="calendar__day" key={index} aria-hidden="true"><Bone className="bone--line bone--short" /></div>
        ))}
      </div>
    </div>
  );
}

function HoursSkeleton() {
  return (
    <div className="hour-grid" role="status" aria-label="در حال بارگذاری">
      <span />
      {Array.from({ length: 7 }, (_, index) => <Bone className="bone--line" key={`day-${index}`} />)}
      {Array.from({ length: 27 }, (_, row) => (
        <span key={row} style={{ display: "contents" }}>
          <Bone className="bone--line" />
          {Array.from({ length: 7 }, (_, column) => <Bone className="bone--cell" key={column} />)}
        </span>
      ))}
    </div>
  );
}

function toast(message, kind = "ok", persist = false) {
  if (!message) return;
  if (persist) {
    sessionStorage.setItem("hamzaban-toast", JSON.stringify({ message, kind }));
    return;
  }
  window.dispatchEvent(new CustomEvent("hamzaban-toast", { detail: { id: `${Date.now()}-${Math.random()}`, message, kind } }));
}

function ToastStack() {
  const [items, setItems] = useState([]);
  useEffect(() => {
    const show = (item) => {
      setItems((list) => [...list, item]);
      window.setTimeout(() => setItems((list) => list.filter((entry) => entry.id !== item.id)), 4200);
    };
    const onToast = (event) => show(event.detail);
    window.addEventListener("hamzaban-toast", onToast);
    const saved = sessionStorage.getItem("hamzaban-toast");
    if (saved) {
      sessionStorage.removeItem("hamzaban-toast");
      try {
        const item = JSON.parse(saved);
        show({ id: "saved", ...item });
      } catch (_) {}
    }
    return () => window.removeEventListener("hamzaban-toast", onToast);
  }, []);
  if (!items.length) return null;
  return (
    <div className="toast-stack">
      {items.map((item) => (
        <p key={item.id} className={item.kind === "error" ? "toast toast--error" : "toast"} role={item.kind === "error" ? "alert" : "status"}>{item.message}</p>
      ))}
    </div>
  );
}

function ThemeButton() {
  return (
    <button className="theme-toggle" type="button" data-theme-toggle aria-label="تغییر پوسته">
      <span className="material-symbols-outlined theme-toggle__moon" aria-hidden="true">dark_mode</span>
      <span className="material-symbols-outlined theme-toggle__sun" aria-hidden="true">light_mode</span>
    </button>
  );
}

function Logout({ compact = false }) {
  return (
    <form className={compact ? "logout-form logout-form--compact" : "logout-form"} data-logout method="post" action="/accounts/logout/">
      <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken()} />
      <button className={compact ? "section-links__button" : "profile-menu__item logout-form__button"} type="submit">
        {compact ? null : <Icon name="logout" />}
        خروج
      </button>
    </form>
  );
}

function Badge({ status, children }) {
  return <span className={`badge badge--${status}`}>{children}</span>;
}

const MeContext = createContext({ loading: true, error: "", data: null });

function MeProvider({ children }) {
  const state = useFetch("/api/me/");
  return <MeContext.Provider value={state}>{children}</MeContext.Provider>;
}

function useMe() {
  return useContext(MeContext);
}

function ClientShell({ section, children }) {
  const { loading, data } = useMe();
  const me = data || {};
  const waiting = loading && !data;
  const items = [
    ["account", "/profile/account/", "manage_accounts", "حساب کاربری", "حساب"],
    ["overview", "/profile/", "dashboard", "نمای کلی", "خانه"],
    ["sessions", "/profile/sessions/", "event", "جلسه‌های من", "جلسه‌ها"],
    ["payments", "/profile/payments/", "receipt_long", "پرداخت‌ها", "پرداخت"],
    ["notifications", "/profile/notifications/", "notifications", "اعلانات", "اعلان"],
  ];
  return (
    <div className="profile-shell">
      <aside className="profile-sidebar">
        <Identity name={me.name || ""} email={me.email || ""} phone={me.phone || ""} loading={waiting} />
        <nav className="profile-menu" aria-label="بخش‌های حساب">
          {items.map(([key, href, icon, label]) => (
            <a className={section === key ? "profile-menu__item is-active" : "profile-menu__item"} key={key} href={href} aria-current={section === key ? "page" : undefined}>
              <Icon name={icon} /> {label}
            </a>
          ))}
          <a className="profile-menu__item" href="/therapists/"><Icon name="search" /> پیدا کردن درمانگر</a>
          <Logout />
        </nav>
      </aside>
      <section className="profile-main">
        <Identity name={me.name || ""} email={me.email || ""} phone={me.phone || ""} bar loading={waiting} />
        <nav className="section-links" aria-label="میانبرهای حساب">
          <a href="/therapists/">درمانگرها</a>
          <Logout compact />
        </nav>
        {children}
      </section>
      <nav className="mobile-profile-nav" aria-label="ناوبری موبایل">
        {items.map(([key, href, icon, , short]) => (
          <a className={section === key ? "is-active" : ""} key={key} href={href} aria-current={section === key ? "page" : undefined}>
            <Icon name={icon} />{short}
          </a>
        ))}
      </nav>
    </div>
  );
}

function TherapistShell({ section, children }) {
  const { loading, data } = useMe();
  const me = data || {};
  const waiting = loading && !data;
  const items = [
    ["profile", "/therapist/profile/", "manage_accounts", "حساب کاربری"],
    ["today", "/therapist/home/", "dashboard", "امروز"],
    ["sessions", "/therapist/sessions/", "event", "جلسه‌ها"],
    ["students", "/therapist/students/", "group", "دانشجوها"],
    ["caseload", "/therapist/caseload/", "psychology", "حال مراجعان"],
    ["tasks", "/therapist/tasks/", "task_alt", "کارها"],
    ["notifications", "/therapist/notifications/", "notifications", "اعلانات"],
    ["income", "/therapist/income/", "payments", "درآمد"],
    ["hours", "/therapist/hours/", "schedule", "ساعت‌ها"],
  ];
  const mobile = items.filter(([key]) => ["today", "sessions", "students", "tasks"].includes(key));
  return (
    <div className="profile-shell">
      <aside className="profile-sidebar">
        <Identity name={me.name || ""} email={me.email || ""} phone={me.phone || ""} photo={me.photo} loading={waiting} />
        <nav className="profile-menu" aria-label="بخش‌های درمانگر">
          {items.map(([key, href, icon, label]) => (
            <a className={section === key ? "profile-menu__item is-active" : "profile-menu__item"} key={key} href={href} aria-current={section === key ? "page" : undefined}>
              <Icon name={icon} /> {label}
            </a>
          ))}
          <Logout />
        </nav>
      </aside>
      <section className="profile-main">
        <Identity name={me.name || ""} email={me.email || ""} phone={me.phone || ""} photo={me.photo} bar loading={waiting} />
        <nav className="section-links" aria-label="میانبرهای درمانگر">
          <a href="/therapist/profile/">حساب کاربری</a>
          <a href="/therapist/notifications/">اعلانات</a>
          <a href="/therapist/caseload/">حال مراجعان</a>
          <a href="/therapist/income/">درآمد</a>
          <a href="/therapist/hours/">ساعت‌ها</a>
          <Logout compact />
        </nav>
        {children}
      </section>
      <nav className="mobile-profile-nav" aria-label="ناوبری موبایل">
        {mobile.map(([key, href, icon, label]) => (
          <a className={section === key ? "is-active" : ""} key={key} href={href} aria-current={section === key ? "page" : undefined}>
            <Icon name={icon} />{label}
          </a>
        ))}
      </nav>
    </div>
  );
}

function Identity({ name, email, phone, photo, bar = false, loading = false }) {
  return (
    <div className={bar ? "profile-identity profile-identity--bar" : "profile-identity"}>
      {photo ? <img className="avatar" src={photo} alt="" /> : <span className="avatar avatar--icon"><Icon name="person" /></span>}
      <div>
        {loading ? <Bone className="bone--title" /> : <strong>{name}</strong>}
        {loading ? <Bone className="bone--line bone--short" /> : <span className="profile-identity__email" dir="ltr" title={email}>{email || "ایمیل ثبت نشده"}</span>}
        {loading || !phone ? null : <span dir="ltr">{phone}</span>}
      </div>
      <ThemeButton />
    </div>
  );
}

function InstallApp({ title, detail, href }) {
  return (
    <section className="landing-section">
      <div className="landing-wrap">
        <div className="install-row">
          <div>
            <h2>{title}</h2>
            <p className="muted">{detail}</p>
          </div>
          <a className="primary-button" href={href} data-reload>نصب برنامه</a>
        </div>
      </div>
    </section>
  );
}

function Home() {
  const { loading, error, data } = useFetch("/api/home/");
  return (
    <>
      <section className="hero">
        <div className="landing-wrap hero__inner">
          <p className="eyebrow">تراپی، از همین‌جا</p>
          <h1>درمانگر مناسب خود را پیدا کنید</h1>
          <p className="hero__lead">هم‌زبان فهرست درمانگرها و زمان‌های آزادشان را نشان می‌دهد تا مسیر جلسه را ساده‌تر ببینید.</p>
          <div className="hero__actions">
            <a className="primary-button" href="/therapists/">دیدن درمانگرها</a>
            <a className="secondary-button" href="/accounts/register/">ساخت حساب</a>
          </div>
        </div>
      </section>
      <section className="landing-section">
        <div className="landing-wrap about-layout">
          <div>
            <p className="eyebrow">آشنایی</p>
            <h2>هم‌زبان چیست؟</h2>
            <p className="muted">هم‌زبان یک وب‌سایت برای مراجع و درمانگر است. مسیر اول تراپی است. مراجع درمانگر تأییدشده را می‌بیند و با رسید آفلاین وقت می‌گیرد.</p>
          </div>
          <ul className="about-points">
            <li><strong>پیدا کردن درمانگر</strong><span>نام، تخصص یا رویکرد را جستجو کنید.</span></li>
            <li><strong>دیدن زمان آزاد</strong><span>برنامهٔ هر درمانگر در صفحهٔ خودش است.</span></li>
            <li><strong>حساب مراجع</strong><span>فضای شخصی برای ادامهٔ مسیر شماست.</span></li>
          </ul>
        </div>
      </section>
      <InstallApp title="برنامهٔ مراجع" detail="برای نصب، اول وارد صفحهٔ ورود مراجع شوید." href="/accounts/login/?app=client&next=/profile/" />
      <section className="landing-section landing-section--soft">
        <div className="landing-wrap">
          <h2 className="visually-hidden">آمار نمونه</h2>
          <Alert>{error}</Alert>
          {loading && !data ? <StatSkeleton /> : (
            <dl className="stat-row">
              {(data?.stats || []).map((stat) => (
                <div key={stat.label}><dt>{stat.label}</dt><dd>{stat.value}</dd></div>
              ))}
            </dl>
          )}
          <p className="stat-note">این عددها نمونهٔ معرفی هستند، نه آمار زنده.</p>
        </div>
      </section>
      <section className="landing-section" id="faq">
        <div className="landing-wrap faq-layout">
          <div>
            <p className="eyebrow">پرسش‌ها</p>
            <h2>سؤال‌های رایج</h2>
          </div>
          <div className="faq-list">
            {loading && !data ? <FaqSkeleton /> : (data?.faqs || []).map((item) => (
              <details className="faq-item" key={item.question}>
                <summary>{item.question}</summary>
                <p>{item.answer}</p>
              </details>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}

function Crumb({ items }) {
  return (
    <nav className="breadcrumb" aria-label="مسیر">
      <ol>
        {items.map((item) => (
          <li key={item.label}>
            {item.href ? <a href={item.href}>{item.label}</a> : <span aria-current="page">{item.label}</span>}
          </li>
        ))}
      </ol>
    </nav>
  );
}

function TherapistList() {
  const path = usePath();
  const query = new URLSearchParams(path.split("?")[1] || "").get("q") || "";
  const { loading, error, data } = useFetch(`/api/therapists/?q=${encodeURIComponent(query)}`);
  return (
    <section className="landing-section">
      <div className="landing-wrap">
        <Crumb items={[{ label: "خانه", href: "/" }, { label: "درمانگرها" }]} />
        <p className="eyebrow">تأییدشده، با وقت آزاد</p>
        <h1>درمانگرها</h1>
        <form className="search-bar" role="search" onSubmit={(event) => { event.preventDefault(); go(`/therapists/?q=${encodeURIComponent(new FormData(event.currentTarget).get("q") || "")}`); }}>
          <label htmlFor="therapist-query">جستجو</label>
          <div className="search-bar__row">
            <input id="therapist-query" name="q" defaultValue={query} placeholder="نام، تخصص یا رویکرد" autoComplete="off" />
            <button className="primary-button" type="submit">جستجو</button>
          </div>
        </form>
        <Alert>{error}</Alert>
        {loading && !data ? <DirectorySkeleton /> : null}
        {data && data.therapists.length ? (
          <div className="therapist-grid">
            {data.therapists.map((item) => (
              <article className="therapist-card" key={item.slug}>
                {item.photo ? <img className="avatar" src={item.photo} alt="" /> : <span className="avatar" aria-hidden="true">{item.name.slice(0, 1)}</span>}
                <div>
                  <h2>{item.name}</h2>
                  <p>{item.approach} · {item.price}</p>
                  <p>{item.specialties.join("، ")}</p>
                  {item.education?.length ? <p>{item.education.join("، ")}</p> : null}
                </div>
                <a className="secondary-button" href={`/therapists/${item.slug}/`}>زمان‌های آزاد</a>
              </article>
            ))}
          </div>
        ) : null}
        {data && !data.therapists.length ? <p className="empty-state">درمانگری با این جستجو پیدا نشد. عبارت دیگری را امتحان کنید.</p> : null}
      </div>
    </section>
  );
}

const WEEK_COUNTS = [2, 4, 6, 8, 10, 12];

function faCount(value) {
  return String(value).replace(/\d/g, (digit) => "۰۱۲۳۴۵۶۷۸۹"[digit]);
}

function meetingSummary(items) {
  if (items.length > 1) return `${items.length} جلسه`;
  return items[0]?.label || "";
}

function weeklySummary(slot, count) {
  return `${slot.name} ها ساعت ${faCount(slot.time)} (${faCount(count)} جلسه).`;
}

function ReserveDialog({ open, onClose, data, slug, initialSlotId = "", mode = "slots" }) {
  const dialog = useRef(null);
  const appliedSlot = useRef("");
  const weeks = data?.weeks || [];
  const [weekIndex, setWeekIndex] = useState(0);
  const [dayKey, setDayKey] = useState("");
  const [step, setStep] = useState("time");
  const [slot, setSlot] = useState(null);
  const [picks, setPicks] = useState([]);
  const [weeklySlot, setWeeklySlot] = useState(null);
  const [weekCount, setWeekCount] = useState(10);
  const [plan, setPlan] = useState(null);
  const [pay, setPay] = useState(null);
  const [payError, setPayError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const node = dialog.current;
    if (!node) return;
    if (open && !node.open) node.showModal();
    if (!open && node.open) node.close();
  }, [open]);
  useEffect(() => {
    if (open) return;
    appliedSlot.current = "";
    setStep("time");
    setSlot(null);
    setPicks([]);
    setWeeklySlot(null);
    setWeekCount(10);
    setPlan(null);
    setPay(null);
    setPayError("");
    setBusy(false);
  }, [open]);
  useEffect(() => {
    if (!open) return;
    const todayWeek = weeks.findIndex((week) => week.days.some((day) => day.badge === "امروز"));
    const firstWithSlots = weeks.findIndex((week) => week.days.some((day) => day.slots.length));
    const index = todayWeek >= 0 ? todayWeek : Math.max(firstWithSlots, 0);
    setWeekIndex(index);
    const today = weeks[index]?.days.find((day) => day.badge === "امروز" && day.slots.length);
    setDayKey(today ? today.key : "");
  }, [open, weeks]);
  useEffect(() => {
    if (!open || mode === "weekly" || !initialSlotId || !weeks.length || appliedSlot.current === String(initialSlotId)) return;
    appliedSlot.current = String(initialSlotId);
    let found = null;
    let label = "";
    weeks.forEach((week) => week.days.forEach((day) => {
      const match = day.slots.find((item) => String(item.id) === String(initialSlotId));
      if (match) {
        found = match;
        label = `${day.label}، ساعت ${match.time}`;
      }
    }));
    if (!found || data?.is_therapist) {
      setPayError(found ? "" : "این وقت دیگر آزاد نیست.");
      setStep("time");
      return;
    }
    const nextSlot = { id: found.id, time: found.time, label };
    setPicks([nextSlot]);
    setSlot(nextSlot);
    setPay(null);
    setPayError("");
    setStep("pay");
  }, [open, mode, initialSlotId, weeks, data?.is_therapist]);
  useEffect(() => {
    if (step !== "pay" || !data?.can_book || mode === "weekly" || picks.length !== 1) return undefined;
    let live = true;
    setPay(null);
    setPayError("");
    api(`/api/book/${slug}/${picks[0].id}/`)
      .then((result) => { if (live) setPay(result); })
      .catch((error) => { if (live) setPayError(error.message); });
    return () => { live = false; };
  }, [step, picks, slug, data?.can_book, mode]);
  const week = weeks[weekIndex];
  const selected = week?.days.find((day) => day.key === dayKey);
  const chosen = mode === "weekly" ? (plan?.meetings || []).filter((item) => item.available) : picks;
  const summary = mode === "weekly" && weeklySlot ? weeklySummary(weeklySlot, chosen.length) : meetingSummary(chosen);
  function choose(item, day) {
    if (data?.is_therapist) return;
    const nextSlot = { id: item.id, time: item.time, name: day.name, label: `${day.label}، ساعت ${item.time}` };
    if (mode === "weekly") {
      setWeeklySlot(nextSlot);
      setPlan(null);
      setPayError("");
      setStep("count");
      return;
    }
    setPicks((current) => current.some((row) => row.id === item.id) ? current.filter((row) => row.id !== item.id) : [...current, nextSlot]);
  }
  async function loadPlan() {
    if (!weeklySlot) return;
    if (!data?.can_book) {
      dialog.current?.close();
      go(`/accounts/login/?next=${encodeURIComponent(`/therapists/${slug}/`)}`);
      return;
    }
    setBusy(true);
    setPayError("");
    try {
      const result = await api(`/api/book/${slug}/weekly/${weeklySlot.id}/?weeks=${weekCount}`);
      setPlan(result);
      setStep("plan");
    } catch (error) {
      setPayError(error.message);
    } finally {
      setBusy(false);
    }
  }
  function openPayment() {
    if (!data?.can_book) {
      dialog.current?.close();
      go(`/accounts/login/?next=${encodeURIComponent(`/therapists/${slug}/`)}`);
      return;
    }
    if (mode === "weekly" && plan) {
      setPay({ amount: plan.amount, notice: plan.notice });
    } else {
      setPay({ amount: (Number(data?.session_price) * picks.length).toFixed(2), notice: data?.notice });
    }
    setPayError("");
    setStep("pay");
  }
  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setPayError("");
    try {
      const body = new FormData(event.currentTarget);
      let result;
      if (mode === "weekly") {
        body.append("weeks", String(weekCount));
        body.append("meetings", String(plan?.available || chosen.length));
        result = await api(`/api/book/${slug}/weekly/${weeklySlot.id}/`, { method: "POST", body });
      } else if (picks.length > 1) {
        picks.forEach((item) => body.append("slots", item.id));
        result = await api(`/api/book/${slug}/many/`, { method: "POST", body });
      } else {
        result = await api(`/api/book/${slug}/${picks[0].id}/`, { method: "POST", body });
      }
      setPay(result);
      setStep("success");
    } catch (error) {
      setPayError(error.message);
    } finally {
      setBusy(false);
    }
  }
  const titles = {
    slots: { time: "انتخاب زمان", pay: "پرداخت", success: "رزرو ثبت شد" },
    weekly: { time: "رزرو هفتگی", count: "چند هفته", plan: "جلسه‌های هفتگی", pay: "پرداخت", success: "رزرو ثبت شد" },
  };
  const title = (titles[mode] || titles.slots)[step] || "رزرو";
  const hint = mode === "weekly"
    ? "ساعتی را انتخاب کنید که هر هفته تکرار شود."
    : (selected ? "یک یا چند ساعت را انتخاب کنید." : `یک روز را انتخاب کنید. وقت‌های امروز هم، اگر حداقل ${data?.notice ?? ""} ساعت دیگر باشند، قابل رزرو هستند.`);
  return (
    <dialog className="reserve-dialog" ref={dialog} onClose={onClose} onClick={(event) => { if (event.target === dialog.current) onClose(); }}>
      <div className="reserve-dialog__sheet">
        {step === "pay" ? null : (
          <div className="record-card__row">
            <h2>{title}</h2>
            <button className="reserve-close" type="button" onClick={onClose} aria-label="بستن"><Icon name="close" /></button>
          </div>
        )}
        {step === "time" ? (
          <>
            {week ? <p className="muted reserve-hint">{hint}</p> : null}
            {week ? (
              <>
                <div className="week-strip">
                  <button className="week-nav" type="button" aria-label="هفته قبل" onClick={() => { setWeekIndex((value) => Math.max(0, value - 1)); setDayKey(""); }} disabled={weekIndex === 0}><Icon name="chevron_right" /></button>
                  <div className="week-days">
                    {week.days.map((day) => (
                      <button className={day.key === dayKey ? "week-day is-selected" : "week-day"} type="button" key={day.key} disabled={!day.slots.length} onClick={() => setDayKey(day.key)}>
                        <span>{day.name}</span>
                        <strong>{day.number}</strong>
                        {day.badge ? <em className="week-day__badge">{day.badge}</em> : <em className="week-day__badge" />}
                      </button>
                    ))}
                  </div>
                  <button className="week-nav" type="button" aria-label="هفته بعد" onClick={() => { setWeekIndex((value) => Math.min(weeks.length - 1, value + 1)); setDayKey(""); }} disabled={weekIndex >= weeks.length - 1}><Icon name="chevron_left" /></button>
                </div>
                {selected ? (
                  <div className="time-list">
                    {selected.slots.map((item) => {
                      const picked = mode !== "weekly" && picks.some((row) => row.id === item.id);
                      return <button className={picked ? "time-chip is-selected" : "time-chip"} type="button" key={item.id} onClick={() => choose(item, selected)}>{item.time}</button>;
                    })}
                  </div>
                ) : null}
                {mode !== "weekly" && picks.length > 1 ? <p className="muted">{picks.length} جلسه انتخاب شده است.</p> : null}
                {mode !== "weekly" ? <button className="primary-button" type="button" disabled={!picks.length} onClick={openPayment}>ادامه</button> : null}
              </>
            ) : <p className="empty-state">فعلاً وقت آزادی نیست.</p>}
            <Alert>{payError}</Alert>
            {data?.is_therapist ? <p className="schedule-note">رزرو از حساب درمانگر انجام نمی‌شود.</p> : null}
          </>
        ) : null}
        {step === "count" && weeklySlot ? (
          <div className="week-count">
            <p className="muted">هر هفته همان ساعت {weeklySlot.time}.</p>
            <p id="week-count-label">تعداد هفته</p>
            <div className="time-list" role="radiogroup" aria-labelledby="week-count-label">
              {WEEK_COUNTS.map((count) => (
                <button className={count === weekCount ? "time-chip is-selected" : "time-chip"} type="button" role="radio" aria-checked={count === weekCount} key={count} onClick={() => setWeekCount(count)}>{faCount(count)}</button>
              ))}
            </div>
            <button className="primary-button" type="button" disabled={busy} onClick={loadPlan}>{busy ? "در حال بررسی…" : "نمایش جلسه‌ها"}</button>
            <Alert>{payError}</Alert>
          </div>
        ) : null}
        {step === "plan" && plan ? (
          <>
            <p className="muted">{plan.available} جلسه از {plan.weeks} هفته آزاد است.</p>
            {plan.meetings.some((item) => !item.available) ? (
              <ul className="series-list">
                {plan.meetings.filter((item) => !item.available).map((item) => (
                  <li className="is-closed" key={item.label}>
                    <span>{item.label}</span>
                    <span>{item.reason}</span>
                  </li>
                ))}
              </ul>
            ) : null}
            {plan.available >= 2 ? <button className="primary-button" type="button" onClick={openPayment}>ادامه و پرداخت</button> : <p className="schedule-note">برای رزرو هفتگی حداقل دو هفته آزاد لازم است.</p>}
          </>
        ) : null}
        {step === "pay" && chosen.length ? (
          <>
            <div className="reserve-person">
              {data?.therapist?.photo ? <img className="avatar" src={data.therapist.photo} alt="" /> : <span className="avatar">{(data?.therapist?.name || "د").slice(0, 1)}</span>}
              <strong>{data?.therapist?.name}</strong>
              <button className="reserve-close" type="button" onClick={onClose} aria-label="بستن"><Icon name="close" /></button>
            </div>
            <p className="muted">حداقل اطلاع قبلی {data?.notice ?? pay?.notice} ساعت است.</p>
            <div className="reserve-when">
              <button className="reserve-edit" type="button" onClick={() => { setStep(mode === "weekly" ? "plan" : "time"); setPayError(""); }}>
                <Icon name="edit" />
                تغییر زمان
              </button>
              <strong>{summary}</strong>
            </div>
            {!data?.can_book ? <a className="primary-button" href={`/accounts/login/?next=${encodeURIComponent(`/therapists/${slug}/`)}`}>ورود برای پرداخت</a> : null}
            {data?.can_book && !pay && !payError ? <FormSkeleton rows={4} /> : null}
            <Alert>{payError}</Alert>
            {data?.can_book && pay ? (
              <form className="stack-form" onSubmit={submit}>
                <label htmlFor="amount">مبلغ پرداخت‌شده</label>
                <input id="amount" name="amount" defaultValue={pay.amount} inputMode="decimal" required />
                <label htmlFor="reference">شماره پیگیری</label>
                <input id="reference" name="reference" required />
                <label htmlFor="note">توضیح برای درمانگر</label>
                <textarea id="note" name="note" rows="3" maxLength={1000} placeholder="موضوع جلسه یا نکته‌ای که درمانگر باید بداند" />
                <label htmlFor="attachment">تصویر رسید</label>
                <input id="attachment" name="attachment" type="file" />
                <button className="primary-button" type="submit" disabled={busy}>{busy ? "در حال ثبت…" : "ثبت رسید"}</button>
              </form>
            ) : null}
          </>
        ) : null}
        {step === "success" && chosen.length ? (
          <div className="reserve-success">
            <Icon name="check_circle" />
            <p>{pay?.message || "رسید ثبت شد و درمانگر آن را می‌بیند."}</p>
            <p className="muted">{summary}</p>
            <a className="primary-button" href="/profile/payments/">دیدن پرداخت‌ها</a>
          </div>
        ) : null}
      </div>
    </dialog>
  );
}

function TherapistDetail({ slug }) {
  const path = usePath();
  const requestedSlot = new URLSearchParams(path.split("?")[1] || "").get("slot") || "";
  const { loading, error, data } = useFetch(`/api/therapists/${slug}/`);
  const [reserveOpen, setReserveOpen] = useState(Boolean(requestedSlot));
  const [reserveMode, setReserveMode] = useState("slots");
  useEffect(() => {
    if (requestedSlot) {
      setReserveMode("slots");
      setReserveOpen(true);
    }
  }, [requestedSlot]);
  function openReserve(mode) {
    setReserveMode(mode);
    setReserveOpen(true);
  }
  function closeReserve() {
    setReserveOpen(false);
    if (!requestedSlot) return;
    window.history.replaceState({}, "", `/therapists/${slug}/`);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }
  const item = data?.therapist;
  const hasTimes = (data?.weeks || []).some((week) => week.days.some((day) => day.slots.length));
  return (
    <article className="landing-section">
      <div className="landing-wrap">
        <Crumb items={[{ label: "خانه", href: "/" }, { label: "درمانگرها", href: "/therapists/" }, { label: item?.name || "درمانگر" }]} />
        <Alert>{error}</Alert>
        {loading && !item ? <DetailSkeleton /> : null}
        {item ? (
          <div className="therapist-layout">
            <div className="therapist-detail">
              <section className="profile-box">
                <h2>اطلاعات درمانگر</h2>
                <header className="therapist-detail__header">
                  {item.photo ? <img className="avatar avatar--large" src={item.photo} alt="" /> : <span className="avatar avatar--large">{item.name.slice(0, 1)}</span>}
                  <div>
                    <h1>{item.name}</h1>
                    <p className="muted">{item.approach}</p>
                  </div>
                </header>
                <dl className="profile-facts">
                  <div><dt>جنسیت</dt><dd>{item.gender || "ثبت نشده"}</dd></div>
                  <div><dt>سال تجربه</dt><dd>{item.years ? `${item.years} سال` : "ثبت نشده"}</dd></div>
                  <div><dt>رویکرد</dt><dd>{item.approach || "ثبت نشده"}</dd></div>
                  <div><dt>منطقه زمانی</dt><dd>{item.timezone_label || item.timezone || "ثبت نشده"}</dd></div>
                  <div><dt>شماره تماس</dt><dd>{item.phone || "ثبت نشده"}</dd></div>
                </dl>
              </section>
              <section className="profile-box">
                <h2>زبان‌ها</h2>
                {item.languages?.length ? <ul className="chip-list">{item.languages.map((name) => <li key={name}>{name}</li>)}</ul> : <p className="muted">ثبت نشده</p>}
              </section>
              <section className="profile-box">
                <h2>تخصص‌ها</h2>
                {item.specialties?.length ? <ul className="chip-list">{item.specialties.map((name) => <li key={name}>{name}</li>)}</ul> : <p className="muted">ثبت نشده</p>}
              </section>
              <section className="profile-box">
                <h2>تحصیلات</h2>
                {item.education?.length ? <ul className="chip-list">{item.education.map((name) => <li key={name}>{name}</li>)}</ul> : <p className="muted">ثبت نشده</p>}
              </section>
              <section className="profile-box">
                <h2>معرفی</h2>
                <p>{item.introduction || "ثبت نشده"}</p>
              </section>
              <section className="profile-box">
                <h2>اطلاعات جواز</h2>
                <dl className="profile-facts">
                  <div><dt>نوع مجوز</dt><dd>{item.license_type || "ثبت نشده"}</dd></div>
                  <div><dt>شماره مجوز</dt><dd>{item.license_number || "ثبت نشده"}</dd></div>
                  <div><dt>کشور صدور</dt><dd>{item.license_country || "ثبت نشده"}</dd></div>
                </dl>
              </section>
            </div>
            <aside className="reserve-card">
              <h2>رزرو جلسه</h2>
              <dl>
                <div><dt>شماره تماس</dt><dd>{item.phone || "ثبت نشده"}</dd></div>
                <div><dt>مدت جلسه</dt><dd>{data.duration}</dd></div>
                <div><dt>قیمت جلسه</dt><dd>{item.price}</dd></div>
              </dl>
              <button className="primary-button" type="button" onClick={() => openReserve("slots")} disabled={!hasTimes}>رزرو</button>
              <button className="secondary-button" type="button" onClick={() => openReserve("weekly")} disabled={!hasTimes}>رزرو هفتگی</button>
              {!hasTimes ? <p className="schedule-note">فعلاً وقت آزادی در ۳۰ روز آینده نیست.</p> : null}
            </aside>
            <ReserveDialog open={reserveOpen} onClose={closeReserve} data={data} slug={item.slug} initialSlotId={requestedSlot} mode={reserveMode} />
          </div>
        ) : null}
      </div>
    </article>
  );
}

function Book({ slug, slotId }) {
  useEffect(() => {
    const next = `/therapists/${decodeURIComponent(slug)}/?slot=${slotId}`;
    window.history.replaceState({}, "", next);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, [slug, slotId]);
  return null;
}

function Login() {
  const params = new URLSearchParams(window.location.search);
  const next = params.get("next") || "";
  const app = params.get("app");
  const installing = app === "client" || app === "therapist";
  async function submit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const result = await api("/api/login/", { method: "POST", body: { username: form.get("username"), password: form.get("password"), next } });
      toast("وارد شدید.", "ok", true);
      window.location.assign(result.next);
    } catch (err) {
      toast(err.message, "error");
    }
  }
  return (
    <section className="login-card">
      {installing ? (
        <>
          <p className="eyebrow">{app === "client" ? "برنامهٔ مراجع" : "برنامهٔ درمانگر"}</p>
          <h1>نصب برنامه</h1>
          <ol className="install-steps">
            <li>این صفحه را در مرورگر گوشی باز کنید. در آیفون Safari و در اندروید Chrome را استفاده کنید.</li>
            <li>منوی مرورگر را باز کنید. در Chrome «نصب برنامه» یا «افزودن به صفحهٔ اصلی» را بزنید. در Safari دکمهٔ اشتراک و سپس «افزودن به صفحهٔ اصلی» را بزنید.</li>
            <li>آیکن هم‌زبان را از صفحهٔ اصلی باز کنید و با فرم زیر وارد شوید.</li>
          </ol>
        </>
      ) : (
        <>
          <p className="eyebrow">خوش آمدید</p>
          <h1>ورود به هم‌زبان</h1>
          <p className="muted">برای دیدن پروفایل، وارد حساب خود شوید.</p>
        </>
      )}
      <form onSubmit={submit}>
        <label htmlFor="id_username">نام کاربری</label>
        <input id="id_username" name="username" autoComplete="username" required autoFocus />
        <label htmlFor="id_password">گذرواژه</label>
        <input id="id_password" name="password" type="password" autoComplete="current-password" required />
        <button className="primary-button" type="submit">ورود</button>
      </form>
      <p className="auth-switch">حساب ندارید؟ <a href={app === "therapist" ? "/therapist/register/" : "/accounts/register/"}>ثبت‌نام</a></p>
    </section>
  );
}

function Register() {
  async function submit(event) {
    event.preventDefault();
    const form = Object.fromEntries(new FormData(event.currentTarget).entries());
    try {
      const result = await api("/api/register/", { method: "POST", body: form });
      toast("حساب ساخته شد.", "ok", true);
      window.location.assign(result.next);
    } catch (err) {
      toast(err.message, "error");
    }
  }
  return (
    <section className="login-card">
      <p className="eyebrow">حساب مراجع</p>
      <h1>ثبت‌نام</h1>
      <form className="stack-form" onSubmit={submit}>
        <label htmlFor="first_name">نام</label>
        <input id="first_name" name="first_name" required />
        <label htmlFor="phone">شماره تماس</label>
        <input id="phone" name="phone" inputMode="tel" autoComplete="tel" />
        <label htmlFor="username">نام کاربری</label>
        <input id="username" name="username" autoComplete="username" required />
        <label htmlFor="email">ایمیل</label>
        <input id="email" name="email" type="email" required />
        <label htmlFor="password1">گذرواژه</label>
        <input id="password1" name="password1" type="password" autoComplete="new-password" required />
        <p className="field-help">حداقل ۸ نویسه، و شبیه نام یا ایمیل نباشد.</p>
        <label htmlFor="password2">تکرار گذرواژه</label>
        <input id="password2" name="password2" type="password" required />
        <button className="primary-button" type="submit">ساخت حساب</button>
      </form>
      <p className="auth-switch">حساب دارید؟ <a href="/accounts/login/">ورود</a></p>
    </section>
  );
}

function TherapistLanding() {
  const { loading, error, data } = useFetch("/api/home/?app=therapist");
  return (
    <>
      <section className="hero">
        <div className="landing-wrap">
          <p className="eyebrow">برای درمانگرها</p>
          <h1>پنل درمانگر هم‌زبان</h1>
          <p className="hero__lead">ساعت‌ها، جلسه‌ها، رسیدها و مراجعان در یک حساب.</p>
          <div className="hero__actions">
            <a className="primary-button" href="/therapist/register/">ثبت‌نام درمانگر</a>
            <a className="secondary-button" href="/accounts/login/">ورود</a>
          </div>
        </div>
      </section>
      <InstallApp title="برنامهٔ درمانگر" detail="برای نصب، اول وارد صفحهٔ ورود درمانگر شوید." href="/accounts/login/?app=therapist&next=/therapist/home/" />
      <section className="landing-section">
        <div className="landing-wrap">
          <p className="eyebrow">شروع</p>
          <h2>مسیر ثبت‌نام</h2>
          {loading && !data ? <ListSkeleton count={3} lines={1} /> : (
            <ol className="about-points">
              {(data?.steps || []).map((step, index) => (
                <li key={step.title}><strong>{index + 1}. {step.title}</strong><span>{step.detail}</span></li>
              ))}
            </ol>
          )}
        </div>
      </section>
      <section className="landing-section landing-section--soft">
        <div className="landing-wrap">
          <h2 className="visually-hidden">قاعده‌های پنل</h2>
          <Alert>{error}</Alert>
          {loading && !data ? <StatSkeleton /> : (
            <dl className="stat-row">
              {(data?.stats || []).map((stat) => (
                <div key={stat.label}><dt>{stat.label}</dt><dd>{stat.value}</dd></div>
              ))}
            </dl>
          )}
          <p className="stat-note">این‌ها قاعده‌های پنل هستند، نه آمار زنده.</p>
        </div>
      </section>
      <section className="landing-section" id="faq">
        <div className="landing-wrap faq-layout">
          <div>
            <p className="eyebrow">پرسش‌ها</p>
            <h2>سؤال‌های رایج</h2>
          </div>
          <div className="faq-list">
            {loading && !data ? <FaqSkeleton /> : (data?.faqs || []).map((item) => (
              <details className="faq-item" key={item.question}>
                <summary>{item.question}</summary>
                <p>{item.answer}</p>
              </details>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}

function ChoiceFields({ options, selected = {} }) {
  if (!options) return null;
  const languages = selected.languages || [];
  const specialties = selected.specialties || [];
  const education = selected.education || [];
  return (
    <>
      <label htmlFor="gender">جنسیت</label>
      <select id="gender" name="gender" defaultValue={selected.gender || "unspecified"}>{options.genders.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select>
      <fieldset>
        <legend>زبان‌ها</legend>
        <ul className="choice-grid">{options.languages.map((item) => <li key={item.value}><label><input type="checkbox" name="languages" value={item.value} defaultChecked={languages.includes(item.value)} />{item.label}</label></li>)}</ul>
      </fieldset>
      <fieldset>
        <legend>تخصص‌ها</legend>
        <ul className="choice-grid">{options.specialties.map((item) => <li key={item.value}><label><input type="checkbox" name="specialties" value={item.value} defaultChecked={specialties.includes(item.value)} />{item.label}</label></li>)}</ul>
      </fieldset>
      <fieldset>
        <legend>تحصیلات</legend>
        <ul className="choice-grid">{(options.education || []).map((item) => <li key={item.value}><label><input type="checkbox" name="education" value={item.value} defaultChecked={education.includes(item.value)} />{item.label}</label></li>)}</ul>
      </fieldset>
      <label htmlFor="approach">رویکرد</label>
      <select id="approach" name="approach" defaultValue={selected.approach || options.approaches[0]?.value}>{options.approaches.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select>
      <label htmlFor="license_type">نوع مجوز</label>
      <select id="license_type" name="license_type" defaultValue={selected.license_type || options.licenses[0]?.value}>{options.licenses.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select>
      <label htmlFor="currency">ارز</label>
      <select id="currency" name="currency" defaultValue={selected.currency || "IRR"}>{options.currencies.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select>
      <label htmlFor="timezone">منطقه زمانی</label>
      <select id="timezone" name="timezone" defaultValue={selected.timezone || "Asia/Tehran"}>{options.timezones.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select>
    </>
  );
}

function TherapistRegister() {
  const { data } = useFetch("/api/therapist-register/");
  async function submit(event) {
    event.preventDefault();
    try {
      const result = await api("/api/therapist-register/", { method: "POST", body: new FormData(event.currentTarget) });
      toast("درخواست ثبت شد.", "ok", true);
      window.location.assign(result.next);
    } catch (err) {
      toast(err.message, "error");
    }
  }
  return (
    <section className="login-card login-card--wide">
      <p className="eyebrow">درمانگر</p>
      <h1>ثبت‌نام درمانگر</h1>
      <form className="stack-form" onSubmit={submit}>
        <label htmlFor="first_name">نام</label>
        <input id="first_name" name="first_name" required />
        <label htmlFor="username">نام کاربری</label>
        <input id="username" name="username" required />
        <label htmlFor="email">ایمیل</label>
        <input id="email" name="email" type="email" required />
        <label htmlFor="therapist-phone">شماره تماس</label>
        <input id="therapist-phone" name="phone" inputMode="tel" autoComplete="tel" />
        <label htmlFor="password1">گذرواژه</label>
        <input id="password1" name="password1" type="password" required />
        <label htmlFor="password2">تکرار گذرواژه</label>
        <input id="password2" name="password2" type="password" required />
        <label htmlFor="display_name">نام نمایشی</label>
        <input id="display_name" name="display_name" required />
        <label htmlFor="years_experience">سال تجربه</label>
        <input id="years_experience" name="years_experience" type="number" min="0" defaultValue="0" required />
        <label htmlFor="license_number">شماره مجوز</label>
        <input id="license_number" name="license_number" required />
        <label htmlFor="license_country">کشور صدور</label>
        <input id="license_country" name="license_country" defaultValue="ایران" required />
        <label htmlFor="license_file">فایل مجوز</label>
        <input id="license_file" name="license_file" type="file" required />
        <label htmlFor="photo">عکس</label>
        <input id="photo" name="photo" type="file" />
        <label htmlFor="introduction">معرفی</label>
        <textarea id="introduction" name="introduction" rows="4" required />
        <label htmlFor="session_price">قیمت جلسه</label>
        <input id="session_price" name="session_price" inputMode="decimal" required />
        <ChoiceFields options={data?.options} />
        <button className="primary-button" type="submit">ثبت درخواست</button>
      </form>
      <p className="auth-switch">حساب مراجع می‌خواهید؟ <a href="/accounts/register/">ثبت‌نام مراجع</a></p>
    </section>
  );
}

function ClientOverview() {
  const { data: me } = useMe();
  const { loading, error, data, reload } = useFetch("/api/client/home/");
  const cards = [
    ["جلسه‌های من", "/profile/sessions/", "event"],
    ["پرداخت‌های من", "/profile/payments/", "receipt_long"],
    ["اعلانات", "/profile/notifications/", "notifications"],
    ["پیدا کردن درمانگر", "/therapists/", "search"],
  ];
  async function saveMood(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const result = await api("/api/client/home/", { method: "POST", body: { emoji: form.get("emoji"), word: form.get("word") } });
      toast(result.message);
      reload();
    } catch (err) {
      toast(err.message, "error");
    }
  }
  async function finish(id) {
    try {
      const result = await api(`/api/client/tasks/${id}/done/`, { method: "POST", body: {} });
      toast(result.message);
      reload();
    } catch (err) {
      toast(err.message, "error");
    }
  }
  return (
    <ClientShell section="overview">
      <p className="eyebrow">فضای شخصی شما</p>
      <h1>نمای کلی</h1>
      <p className="welcome-line"><span className="material-symbols-outlined" aria-hidden="true">waving_hand</span>سلام، {me?.name || ""}</p>
      <Alert>{error}</Alert>
      {loading && !data ? (
        <>
          <section className="record-card"><FormSkeleton rows={2} /></section>
          <ListSkeleton count={2} />
        </>
      ) : null}
      {data ? (
        <>
          <section className="record-card">
            <h2>حال امروز</h2>
            <form className="stack-form" key={`${data.mood?.emoji || ""}-${data.mood?.word || ""}`} onSubmit={saveMood}>
              <div className="choice-grid" role="radiogroup" aria-label="حال امروز">
                {(data.moods || []).map((item) => (
                  <label key={item.emoji}>
                    <input type="radio" name="emoji" value={item.emoji} defaultChecked={data.mood?.emoji === item.emoji} required />
                    {item.emoji} {item.label}
                  </label>
                ))}
              </div>
              <label htmlFor="mood-word">یک کلمه</label>
              <input id="mood-word" name="word" maxLength={40} defaultValue={data.mood?.word || ""} required />
              <button className="primary-button" type="submit">ثبت حال</button>
            </form>
          </section>
          <section>
            <h2>کارهای روزانه</h2>
            <div className="panel-grid">
              {(data.tasks || []).map((item) => (
                <article className="record-card" key={item.id}>
                  <div className="record-card__row"><strong>{item.title}</strong><Badge status={item.status}>{item.status_label}</Badge></div>
                  <p className="muted">{item.kind}</p>
                  <p>{item.body}</p>
                  {item.reward ? <p className="reward">{item.reward}</p> : null}
                  {item.done ? null : <button className="secondary-button" type="button" onClick={() => finish(item.id)}>انجام شد</button>}
                </article>
              ))}
            </div>
            {!data.tasks.length ? <p className="empty-state">برای امروز کاری نیست.</p> : null}
          </section>
        </>
      ) : null}
      <div className="overview-grid">
        {cards.map(([title, href, icon]) => (
          <a className="overview-card" key={title} href={href}>
            <span className="overview-card__icon material-symbols-outlined" aria-hidden="true">{icon}</span>
            <span>{title}</span>
          </a>
        ))}
      </div>
    </ClientShell>
  );
}

function ClientAccount() {
  const { loading, error, data, reload } = useFetch("/api/client/account/");
  async function submit(event) {
    event.preventDefault();
    const form = Object.fromEntries(new FormData(event.currentTarget).entries());
    try {
      const result = await api("/api/client/account/", { method: "POST", body: { ...form, telegram_username: form.telegram } });
      toast(result.message);
      reload();
    } catch (err) {
      toast(err.message, "error");
    }
  }
  return (
    <ClientShell section="account">
      <p className="eyebrow">حساب</p>
      <h1>حساب کاربری</h1>
      {loading && !data ? <FormSkeleton rows={3} /> : null}
      <Alert>{error}</Alert>
      {data ? (
        <form className="stack-form" onSubmit={submit}>
          <label htmlFor="account-name">نام</label>
          <input id="account-name" name="first_name" defaultValue={data.first_name} required />
          <label htmlFor="account-phone">شماره تماس</label>
          <input id="account-phone" name="phone" inputMode="tel" autoComplete="tel" defaultValue={data.phone || ""} />
          <label htmlFor="account-email">ایمیل</label>
          <input id="account-email" name="email" type="email" defaultValue={data.email} required />
          <label htmlFor="account-telegram">تلگرام</label>
          <input id="account-telegram" name="telegram" defaultValue={data.telegram} autoComplete="off" placeholder="username" />
          <p className="field-help">نام کاربری تلگرام، بدون @. اعلان‌ها در خود برنامه می‌آیند.</p>
          <button className="primary-button" type="submit">ذخیره</button>
        </form>
      ) : null}
    </ClientShell>
  );
}

function ClientSessions() {
  const path = usePath();
  const params = new URLSearchParams(path.split("?")[1] || "");
  const { loading, error, data } = useFetch(`/api/client/sessions/?year=${params.get("year") || ""}&month=${params.get("month") || ""}`);
  async function cancel(id) {
    try {
      const result = await api("/api/client/sessions/", { method: "POST", body: { booking: id } });
      toast(result.message);
      go(path);
    } catch (err) {
      toast(err.message, "error");
    }
  }
  const calendar = data?.calendar;
  return (
    <ClientShell section="sessions">
      <p className="eyebrow">تقویم</p>
      <h1>جلسه‌های من</h1>
      <Alert>{error}</Alert>
      {loading && !data ? (
        <>
          <CalendarSkeleton />
          <ListSkeleton />
        </>
      ) : null}
      {calendar ? (
        <div data-session-calendar>
          <div className="calendar-head">
            <a className="secondary-button" href={`/profile/sessions/?year=${calendar.prev.year}&month=${calendar.prev.month}`}>ماه قبل</a>
            <strong>{calendar.title}</strong>
            <a className="secondary-button" href={`/profile/sessions/?year=${calendar.next.year}&month=${calendar.next.month}`}>ماه بعد</a>
          </div>
          <div className="calendar">
            {calendar.weekdays.map((name) => <span className="calendar__name" key={name}>{name}</span>)}
            {calendar.weeks.flat().map((day, index) => (
              day ? (
                <div className="calendar__day" key={`${day.day}-${index}`}>
                  <strong>{day.day}</strong>
                  {day.items.map((item) => (
                    <span className="calendar-session" key={`${item.time}-${item.name}`}>
                      <small>{item.name}</small>
                      <Badge status={item.status}>{item.time}</Badge>
                      {item.meet_url ? <a href={item.meet_url} target="_blank" rel="noopener">ورود</a> : null}
                    </span>
                  ))}
                </div>
              ) : <div className="calendar__day is-empty" key={`empty-${index}`} />
            ))}
          </div>
        </div>
      ) : null}
      <h2>فهرست</h2>
      <div className="panel-grid">
        {(data?.bookings || []).map((item) => (
          <article className="record-card" id={`booking-${item.id}`} key={item.id}>
            <div className="record-card__row">
              <strong>{item.therapist}</strong>
              <Badge status={item.status}>{item.status_label}</Badge>
            </div>
            <p>{item.date}، ساعت {item.time}</p>
            {item.meet_url || item.calendar_url ? (
              <div className="session-actions">
                {item.meet_url ? <a className="primary-button" href={item.meet_url} target="_blank" rel="noopener">ورود به جلسه</a> : null}
                {item.calendar_url ? <a className="secondary-button" href={item.calendar_url} target="_blank" rel="noopener">افزودن به تقویم گوگل</a> : null}
              </div>
            ) : null}
            {item.can_cancel ? <button className="danger-button" type="button" onClick={() => cancel(item.id)}>لغو جلسه</button> : null}
          </article>
        ))}
      </div>
    </ClientShell>
  );
}

function ClientPayments() {
  const { loading, error, data } = useFetch("/api/client/payments/");
  return (
    <ClientShell section="payments">
      <p className="eyebrow">رسید آفلاین</p>
      <h1>پرداخت‌های من</h1>
      <Alert>{error}</Alert>
      {loading && !data ? <ListSkeleton /> : null}
      <div className="panel-grid">
        {(data?.receipts || []).map((item) => (
          <article className="record-card payment-card" id={`receipt-${item.id}`} key={item.id}>
            <div className="record-card__row">
              <strong>{item.amount}</strong>
              <Badge status={item.status}>{item.status_label}</Badge>
            </div>
            <div className="payment-card__meta">
              <span>پیگیری {item.reference}</span>
              <Badge status={item.booking_status}>{item.booking_label}</Badge>
              {item.file ? <a href={item.file}>فایل رسید</a> : null}
            </div>
          </article>
        ))}
      </div>
      {data && !data.receipts.length ? <p className="empty-state">هنوز رسیدی نفرستاده‌اید.</p> : null}
    </ClientShell>
  );
}

function Notes({ path, section, shell: Shell }) {
  const { loading, error, data } = useFetch(path);
  return (
    <Shell section={section}>
      <p className="eyebrow">خبرها</p>
      <h1>اعلانات</h1>
      <Alert>{error}</Alert>
      {loading && !data ? <ListSkeleton /> : null}
      <div className="panel-grid">
        {(data?.notes || []).map((item) => {
          const body = (
            <>
              <div className="record-card__row"><strong>{item.title}</strong><Badge status={item.status}>{item.status_label}</Badge></div>
              <p className="muted">{item.when}</p>
              <p>{item.body}</p>
            </>
          );
          return item.link ? <a className="record-card" href={item.link} key={item.id}>{body}</a> : <article className="record-card" key={item.id}>{body}</article>;
        })}
      </div>
      {data && !data.notes.length ? <p className="empty-state">خبری نیست.</p> : null}
    </Shell>
  );
}

function TherapistToday() {
  const { loading, error, data } = useFetch("/api/therapist/home/");
  return (
    <TherapistShell section="today">
      <p className="eyebrow">پنل درمانگر</p>
      <h1>امروز</h1>
      <Alert>{error}</Alert>
      {loading && !data ? (
        <>
          <ListSkeleton count={2} />
          <ListSkeleton count={2} lines={1} />
        </>
      ) : null}
      {data ? <h2>جلسه‌های امروز</h2> : null}
      {(data?.sessions || []).map((item) => (
        <article className="record-card" key={item.id}>
          <div className="record-card__row"><strong>{item.client}</strong><Badge status={item.status}>{item.status_label}</Badge></div>
          <p>{item.time}</p>
          {item.prep ? <p>{item.prep}</p> : null}
        </article>
      ))}
      {data && !data.sessions.length ? <p className="empty-state">برای امروز جلسه‌ای نیست.</p> : null}
      {data ? <h2>کارهای امروز</h2> : null}
      {(data?.tasks || []).map((item) => (
        <article className="record-card" key={item.id}>
          <div className="record-card__row"><strong>{item.title}</strong><Badge status={item.status}>{item.status_label}</Badge></div>
          <p>{item.client} · {item.kind}</p>
        </article>
      ))}
      {data && !data.tasks.length ? <p className="empty-state">برای امروز کاری نفرستاده‌اید. از بخش کارها می‌توانید تمرین یا یادآور بسازید.</p> : null}
    </TherapistShell>
  );
}

function TherapistStudents() {
  const { loading, error, data } = useFetch("/api/therapist/students/");
  return (
    <TherapistShell section="students">
      <div className="record-card__row"><h1>دانشجوها</h1><a className="primary-button" href="/therapist/students/add/">مراجع تازه</a></div>
      <Alert>{error}</Alert>
      {loading && !data ? <ListSkeleton lines={1} /> : null}
      <div className="panel-grid">
        {(data?.students || []).map((item) => <a className="record-card" key={item.id} href={`/therapist/students/${item.id}/`}><strong>{item.name}</strong></a>)}
      </div>
    </TherapistShell>
  );
}

function AddStudent() {
  async function submit(event) {
    event.preventDefault();
    const form = Object.fromEntries(new FormData(event.currentTarget).entries());
    try {
      const result = await api("/api/therapist/students/add/", { method: "POST", body: form });
      toast(result.message, "ok", true);
      window.location.assign(result.next);
    } catch (err) {
      toast(err.message, "error");
    }
  }
  return (
    <TherapistShell section="students">
      <h1>مراجع تازه</h1>
      <form className="stack-form" onSubmit={submit}>
        <label htmlFor="student-name">نام</label>
        <input id="student-name" name="first_name" required />
        <label htmlFor="student-username">نام کاربری</label>
        <input id="student-username" name="username" required />
        <label htmlFor="student-email">ایمیل</label>
        <input id="student-email" name="email" type="email" required />
        <label htmlFor="student-password">گذرواژهٔ اولیه</label>
        <input id="student-password" name="password" type="password" required />
        <button className="primary-button" type="submit">افزودن</button>
      </form>
    </TherapistShell>
  );
}

function Crm({ userId }) {
  const { loading, error, data } = useFetch(`/api/therapist/students/${userId}/`);
  async function submit(event) {
    event.preventDefault();
    const form = Object.fromEntries(new FormData(event.currentTarget).entries());
    try {
      const result = await api(`/api/therapist/students/${userId}/`, { method: "POST", body: form });
      toast(result.message);
    } catch (err) {
      toast(err.message, "error");
    }
  }
  const record = data?.record;
  return (
    <TherapistShell section="students">
      <h1>{data?.client?.name || "پرونده"}</h1>
      <Alert>{error}</Alert>
      {loading && !data ? (
        <>
          <FormSkeleton rows={4} />
          <ListSkeleton count={2} lines={1} />
        </>
      ) : null}
      {record ? (
        <form className="stack-form" onSubmit={submit}>
          <label htmlFor="notes">یادداشت</label>
          <textarea id="notes" name="notes" rows="4" defaultValue={record.notes} />
          <label htmlFor="mind_map">نقشهٔ ذهن</label>
          <textarea id="mind_map" name="mind_map" rows="4" defaultValue={record.mind_map} />
          <label htmlFor="reports">گزارش‌ها</label>
          <textarea id="reports" name="reports" rows="4" defaultValue={record.reports} />
          <label htmlFor="pre_session_summary">خلاصهٔ پیش از جلسه</label>
          <textarea id="pre_session_summary" name="pre_session_summary" rows="4" defaultValue={record.pre_session_summary} />
          <button className="primary-button" type="submit">ذخیرهٔ پرونده</button>
        </form>
      ) : null}
      {data ? <h2>جلسه‌ها</h2> : null}
      {(data?.sessions || []).map((item) => (
        <article className="record-card" key={item.id}>
          <div className="record-card__row"><strong>{item.date}، {item.time}</strong><Badge status={item.status}>{item.status_label}</Badge></div>
        </article>
      ))}
      {data ? <h2>حال</h2> : null}
      {(data?.moods || []).map((item, index) => <p key={`${item.when}-${index}`}>{item.when}: {item.emoji} {item.word}</p>)}
    </TherapistShell>
  );
}

function Caseload() {
  const path = usePath();
  const client = new URLSearchParams(path.split("?")[1] || "").get("client") || "";
  const { loading, error, data } = useFetch(`/api/therapist/caseload/?client=${client}`);
  return (
    <TherapistShell section="caseload">
      <h1>حال مراجعان</h1>
      <Alert>{error}</Alert>
      {loading && !data ? <ListSkeleton count={4} lines={1} /> : null}
      <nav className="section-links">
        <a href="/therapist/caseload/">همه</a>
        {(data?.students || []).map((item) => <a key={item.id} href={`/therapist/caseload/?client=${item.id}`}>{item.name}</a>)}
      </nav>
      <ul className="choice-grid">
        {(data?.summary || []).map((item) => <li key={item.emoji}>{item.emoji} {item.label}: {item.count}</li>)}
      </ul>
      {(data?.logs || []).map((item) => <p key={item.id}>{item.when} · {item.client}: {item.emoji} {item.word}</p>)}
      {(data?.quiet || []).map((item) => <p key={item.id} className="muted">{item.name} این هفته حالی ثبت نکرده است.</p>)}
    </TherapistShell>
  );
}

function Tasks() {
  const { loading, error, data } = useFetch("/api/therapist/tasks/");
  async function submit(event) {
    event.preventDefault();
    const form = Object.fromEntries(new FormData(event.currentTarget).entries());
    try {
      const result = await api("/api/therapist/tasks/", { method: "POST", body: form });
      toast(result.message);
      go("/therapist/tasks/");
    } catch (err) {
      toast(err.message, "error");
    }
  }
  return (
    <TherapistShell section="tasks">
      <h1>کارها</h1>
      <Alert>{error}</Alert>
      {loading && !data ? (
        <>
          <FormSkeleton rows={4} />
          <ListSkeleton />
        </>
      ) : null}
      {data ? <form className="stack-form" onSubmit={submit}>
        <label htmlFor="task-client">مراجع</label>
        <select id="task-client" name="client" required>
          {(data?.clients || []).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
        <label htmlFor="task-kind">نوع</label>
        <select id="task-kind" name="kind"><option value="practice">تمرین</option><option value="reminder">یادآور</option></select>
        <label htmlFor="task-title">عنوان</label>
        <input id="task-title" name="title" required />
        <label htmlFor="task-body">شرح</label>
        <textarea id="task-body" name="body" rows="3" required />
        <label htmlFor="task-reward">پاداش</label>
        <input id="task-reward" name="reward" />
        <label htmlFor="task-due">تاریخ</label>
        <input id="task-due" name="due_on" type="date" required />
        <button className="primary-button" type="submit">ثبت کار</button>
      </form> : null}
      <div className="panel-grid">
        {(data?.tasks || []).map((item) => (
          <article className="record-card" id={`task-${item.id}`} key={item.id}>
            <div className="record-card__row"><strong>{item.title}</strong><Badge status={item.status}>{item.status_label}</Badge></div>
            <p className="muted">{item.kind}</p>
            <p>{item.client} · {item.due}</p>
            <p>{item.body}</p>
            {item.reward ? <p className="reward">{item.reward}</p> : null}
          </article>
        ))}
      </div>
    </TherapistShell>
  );
}

function Income() {
  const { loading, error, data } = useFetch("/api/therapist/income/");
  const groups = [
    ["دریافت‌شده", data?.received || []],
    ["در انتظار", data?.pending || []],
    ["بازپرداخت", data?.refunded || []],
  ];
  return (
    <TherapistShell section="income">
      <h1>درآمد</h1>
      <Alert>{error}</Alert>
      {loading && !data ? <ListSkeleton /> : null}
      {data ? (data.totals || []).map((item) => <p key={item.currency}><strong>{item.label}</strong></p>) : null}
      {data ? groups.map(([title, rows]) => (
        <section key={title}>
          <h2>{title}</h2>
          {rows.map((item) => (
            <article className="record-card" key={item.id}>
              <div className="record-card__row"><strong>{item.amount}</strong><Badge status={item.status}>{item.status_label}</Badge></div>
              <p>{item.client} · {item.reference}</p>
            </article>
          ))}
          {!rows.length ? <p className="empty-state">موردی نیست.</p> : null}
        </section>
      )) : null}
    </TherapistShell>
  );
}

function TherapistProfile() {
  const { loading, error, data } = useFetch("/api/therapist/profile/");
  const profile = data?.profile;
  async function submit(event) {
    event.preventDefault();
    try {
      const result = await api("/api/therapist/profile/", { method: "POST", body: new FormData(event.currentTarget) });
      toast(result.message);
    } catch (err) {
      toast(err.message, "error");
    }
  }
  return (
    <TherapistShell section="profile">
      <h1>حساب کاربری</h1>
      <Alert>{error}</Alert>
      {loading && !profile ? <FormSkeleton rows={6} /> : null}
      {profile ? <p><Badge status={profile.status}>{profile.status_label}</Badge></p> : null}
      {profile?.rejection ? <p className="form-error">علت رد: {profile.rejection}</p> : null}
      {profile?.google_email ? <p>تقویم گوگل وصل است: {profile.google_email}</p> : null}
      {profile && !profile.google_email ? <p><a className="secondary-button" href="/therapist/calendar/connect/" data-reload="true">اتصال تقویم گوگل</a></p> : null}
      {profile ? (
        <form className="stack-form" onSubmit={submit}>
          <label htmlFor="display_name">نام نمایشی</label>
          <input id="display_name" name="display_name" defaultValue={profile.display_name} required />
          <label htmlFor="years_experience">سال تجربه</label>
          <input id="years_experience" name="years_experience" type="number" defaultValue={profile.years_experience} required />
          <label htmlFor="license_number">شماره مجوز</label>
          <input id="license_number" name="license_number" defaultValue={profile.license_number} required />
          <label htmlFor="license_country">کشور صدور</label>
          <input id="license_country" name="license_country" defaultValue={profile.license_country} required />
          <label htmlFor="phone">شماره تماس</label>
          <input id="phone" name="phone" defaultValue={profile.phone || ""} inputMode="tel" />
          <label htmlFor="introduction">معرفی</label>
          <textarea id="introduction" name="introduction" rows="4" defaultValue={profile.introduction} required />
          <label htmlFor="session_price">قیمت جلسه</label>
          <input id="session_price" name="session_price" defaultValue={profile.session_price} required />
          <label htmlFor="photo">عکس</label>
          <input id="photo" name="photo" type="file" />
          <label htmlFor="license_file">فایل مجوز</label>
          <input id="license_file" name="license_file" type="file" />
          <ChoiceFields options={data.options} selected={profile} />
          <button className="primary-button" type="submit">ذخیره</button>
        </form>
      ) : null}
    </TherapistShell>
  );
}

function HourGrid({ rows, dayNames, chosen, onChange }) {
  const values = rows.flatMap((row) => row.cells.map((cell) => cell.value));
  const allOn = values.length > 0 && values.every((value) => chosen.has(value));
  const someOn = values.some((value) => chosen.has(value));
  function setMany(targets, on) {
    const next = new Set(chosen);
    targets.forEach((value) => (on ? next.add(value) : next.delete(value)));
    onChange(next);
  }
  return (
    <div className="hour-grid" role="group" aria-label="ساعت‌های هفتگی">
      <label className="hour-grid__toggle">
        <input type="checkbox" checked={allOn} ref={(node) => { if (node) node.indeterminate = someOn && !allOn; }} onChange={() => setMany(values, !allOn)} aria-label="همه ساعت‌ها" />
        <span>همه</span>
      </label>
      {dayNames.map((name, index) => {
        const dayValues = rows.map((row) => row.cells[index].value);
        const dayOn = dayValues.every((value) => chosen.has(value));
        const daySome = dayValues.some((value) => chosen.has(value));
        return (
          <label className="hour-grid__toggle" key={name}>
            <input type="checkbox" checked={dayOn} ref={(node) => { if (node) node.indeterminate = daySome && !dayOn; }} onChange={() => setMany(dayValues, !dayOn)} aria-label={`همه ساعت‌های ${name}`} />
            <strong>{name}</strong>
          </label>
        );
      })}
      {rows.map((row) => (
        <span key={row.time} style={{ display: "contents" }}>
          <span>{row.time}</span>
          {row.cells.map((cell) => (
            <label key={cell.value}>
              <input type="checkbox" name="cells" value={cell.value} checked={chosen.has(cell.value)} onChange={() => {
                const next = new Set(chosen);
                if (next.has(cell.value)) next.delete(cell.value);
                else next.add(cell.value);
                onChange(next);
              }} />
            </label>
          ))}
        </span>
      ))}
    </div>
  );
}

function Hours() {
  const { loading, error, data } = useFetch("/api/therapist/hours/");
  const [chosen, setChosen] = useState(() => new Set());
  useEffect(() => {
    if (!data?.rows) return;
    const next = new Set();
    data.rows.forEach((row) => row.cells.forEach((cell) => { if (cell.checked) next.add(cell.value); }));
    setChosen(next);
  }, [data]);
  async function save(event) {
    event.preventDefault();
    try {
      const result = await api("/api/therapist/hours/", { method: "POST", body: { "save-hours": "1", cells: [...chosen] } });
      toast(result.message);
      go("/therapist/hours/");
    } catch (err) {
      toast(err.message, "error");
    }
  }
  async function closeDay(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const result = await api("/api/therapist/hours/", { method: "POST", body: { on: form.get("on"), all_day: form.get("all_day") === "on", start: form.get("start") } });
      toast(result.message);
      go("/therapist/hours/");
    } catch (err) {
      toast(err.message, "error");
    }
  }
  async function remove(id) {
    try {
      const result = await api("/api/therapist/hours/", { method: "POST", body: { "delete-closure": id } });
      toast(result.message);
      go("/therapist/hours/");
    } catch (err) {
      toast(err.message, "error");
    }
  }
  return (
    <TherapistShell section="hours">
      <h1>ساعت‌های من</h1>
      <p className="muted">شبکه از ۹ تا ۲۲ با گام ۳۰ دقیقه است.</p>
      <Alert>{error}</Alert>
      {loading && !data ? <HoursSkeleton /> : null}
      {data ? <p>وقت آزاد الان: {data.open_count}</p> : null}
      {data ? (
        <form onSubmit={save}>
          <HourGrid rows={data.rows} dayNames={data.day_names} chosen={chosen} onChange={setChosen} />
          <button className="primary-button" type="submit">ذخیرهٔ ساعت‌ها</button>
        </form>
      ) : null}
      <h2>بستن روز یا ساعت</h2>
      <form className="stack-form" onSubmit={closeDay}>
        <label htmlFor="on">تاریخ شمسی</label>
        <input id="on" name="on" placeholder="1404-08-21" required />
        <label><input type="checkbox" name="all_day" /> بستن همهٔ روز</label>
        <label htmlFor="start">ساعت</label>
        <select id="start" name="start"><option value="">یک ساعت</option>{(data?.times || []).map((item) => <option key={item}>{item}</option>)}</select>
        <button className="secondary-button" type="submit">ثبت استثنا</button>
      </form>
      {(data?.closures || []).map((item) => (
        <p key={item.id}>{item.label} <button className="danger-button" type="button" onClick={() => remove(item.id)}>حذف</button></p>
      ))}
    </TherapistShell>
  );
}

function TherapistSessions() {
  const { loading, error, data } = useFetch("/api/therapist/sessions/");
  async function act(booking, action, extra = {}) {
    try {
      const result = await api("/api/therapist/sessions/", { method: "POST", body: { booking, action, ...extra } });
      toast(result.message);
      go("/therapist/sessions/");
    } catch (err) {
      toast(err.message, "error");
    }
  }
  function Card({ item }) {
    return (
      <article className="record-card" id={`booking-${item.id}`}>
        <div className="record-card__row"><strong>{item.client}</strong><Badge status={item.status}>{item.status_label}</Badge></div>
        <p>{item.date}، ساعت {item.time} · {item.price}</p>
        {item.note ? <p>{item.note}</p> : null}
        {item.receipt ? <p>رسید {item.receipt.reference}: <Badge status={item.receipt.status}>{item.receipt.status_label}</Badge></p> : null}
        {item.receipt?.file ? <a className="secondary-button" href={item.receipt.file}>فایل رسید</a> : null}
        <div className="button-row">
          {item.status === "awaiting" ? <button className="primary-button" type="button" onClick={() => act(item.id, "accept")}>تأیید رسید</button> : null}
          {item.status === "awaiting" ? <button className="danger-button" type="button" onClick={() => act(item.id, "reject")}>رد رسید</button> : null}
          {item.status === "awaiting" || item.status === "confirmed" ? <button className="danger-button" type="button" onClick={() => act(item.id, "cancel")}>لغو</button> : null}
          {item.status === "confirmed" ? <button className="secondary-button" type="button" onClick={() => act(item.id, "complete")}>انجام شد</button> : null}
        </div>
        <form className="stack-form" onSubmit={(event) => { event.preventDefault(); const form = new FormData(event.currentTarget); act(item.id, "update", { meet_url: form.get("meet_url"), summary: form.get("summary") }); }}>
          <label htmlFor={`meet-${item.id}`}>پیوند ورود</label>
          <input id={`meet-${item.id}`} name="meet_url" type="url" defaultValue={item.meet_url} />
          <label htmlFor={`summary-${item.id}`}>خلاصه برای مراجع</label>
          <textarea id={`summary-${item.id}`} name="summary" rows="3" defaultValue={item.summary} />
          <button className="secondary-button" type="submit">ذخیرهٔ جلسه</button>
        </form>
      </article>
    );
  }
  return (
    <TherapistShell section="sessions">
      <h1>جلسه‌ها</h1>
      <Alert>{error}</Alert>
      {loading && !data ? <ListSkeleton count={2} lines={3} /> : null}
      {data ? <h2>پیشِ رو</h2> : null}
      <div className="panel-grid">{(data?.upcoming || []).map((item) => <Card key={item.id} item={item} />)}</div>
      {data ? <h2>گذشته</h2> : null}
      <div className="panel-grid">{(data?.earlier || []).map((item) => <Card key={item.id} item={item} />)}</div>
    </TherapistShell>
  );
}

function App() {
  const path = usePath();
  const [pathname, search] = [path.split("?")[0], path.includes("?") ? path.slice(path.indexOf("?")) : ""];
  const route = pathname.endsWith("/") ? pathname : `${pathname}/`;
  useEffect(() => {
    const titles = {
      "/": "هم‌زبان | درمانگر مناسب خود را پیدا کنید",
      "/profile/": "پروفایل مراجع | هم‌زبان",
      "/therapist/home/": "امروز | هم‌زبان",
    };
    document.title = titles[route] || "هم‌زبان";
  }, [route]);
  let match;
  let page = <p className="empty-state">این صفحه پیدا نشد.</p>;
  if (route === "/") page = <Home />;
  else if (route === "/therapists/") page = <TherapistList />;
  else if ((match = route.match(/^\/therapists\/([^/]+)\/book\/(\d+)\/$/))) page = <Book slug={match[1]} slotId={match[2]} />;
  else if ((match = route.match(/^\/therapists\/([^/]+)\/$/)) && match[1] !== "photo") page = <TherapistDetail slug={decodeURIComponent(match[1])} />;
  else if (route === "/accounts/login/") page = <Login />;
  else if (route === "/accounts/register/") page = <Register />;
  else if (route === "/therapist/") page = <TherapistLanding />;
  else if (route === "/therapist/register/") page = <TherapistRegister />;
  else if (route === "/profile/") page = <ClientOverview />;
  else if (route === "/profile/account/") page = <ClientAccount />;
  else if (route === "/profile/sessions/") page = <ClientSessions key={search} />;
  else if (route === "/profile/payments/") page = <ClientPayments />;
  else if (route === "/profile/notifications/") page = <Notes path="/api/client/notifications/" section="notifications" shell={ClientShell} />;
  else if (route === "/therapist/home/") page = <TherapistToday />;
  else if (route === "/therapist/notifications/") page = <Notes path="/api/therapist/notifications/" section="notifications" shell={TherapistShell} />;
  else if (route === "/therapist/students/") page = <TherapistStudents />;
  else if (route === "/therapist/students/add/") page = <AddStudent />;
  else if ((match = route.match(/^\/therapist\/students\/(\d+)\/$/))) page = <Crm userId={match[1]} />;
  else if (route === "/therapist/caseload/") page = <Caseload key={search} />;
  else if (route === "/therapist/tasks/") page = <Tasks />;
  else if (route === "/therapist/income/") page = <Income />;
  else if (route === "/therapist/profile/") page = <TherapistProfile />;
  else if (route === "/therapist/hours/") page = <Hours />;
  else if (route === "/therapist/sessions/") page = <TherapistSessions />;
  return <MeProvider>{page}<ToastStack /></MeProvider>;
}

const mount = document.getElementById("app");
if (mount) createRoot(mount).render(<App />);
