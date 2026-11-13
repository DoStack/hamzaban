# Hamzaban project guide

These instructions apply to work in this repository. Follow the current request and the repository's actual files; roadmap items are context, not authorization to build every planned feature.

## Project status and direction

- The GitHub repository is `https://github.com/DoStack/hamzaban`. This local checkout is connected to it on `main`; keep commits and pushes separate from local setup unless requested.
- Hamzaban uses Django, PostgreSQL, Django templates, and React JavaScript bundled locally for interactive client experiences.
- The first customer-facing area is the client profile. The admin experience uses Django Unfold.
- Vercel Hobby is a planned deployment target. Deployment access will be provided later; do not deploy or add credentials before then. Recheck the runtime, database, static-file, and background-job requirements when deployment work is requested.
- The current starter establishes the shared project shell and profile layout only. Do not implement roadmap features until asked.

## Product context

The supplied roadmap describes one website with a client PWA, a therapist PWA, and an admin panel. Therapy is the first course; guitar and coaching are later possibilities. The MVP roadmap includes client and therapist accounts and profiles, therapist discovery, availability and booking, offline receipt review, sessions, cancellation or rescheduling, reviews, notifications, therapist verification and service management, and a basic admin dashboard. Sessions are planned for Google Meet and the appointment calendar currently points to zeeg.me. The live-session assistant and its advanced capabilities are later work.

Use **client** and **therapist** for shared product roles. Treat coaching, guitar, and other professions as future scope unless a task explicitly asks for them. The roadmap is product context; confirm the requested slice before implementing it.

## Start and scope a task

1. Read the relevant issue or product brief when one exists. State a testable outcome and clarify decisions that change that outcome.
2. Inspect the current repository, its manifests, scripts, and existing GitHub changes before choosing commands or changing shared behavior. Do not assume Service45 commands or layouts are already installed here.
3. Keep each change focused. Check callers, related templates, and existing patterns before replacing shared behavior. Coordinate overlapping work when other contributors or pull requests exist.

## Reuse Service45 as the starting reference

Use `/Users/khodro45/Desktop/codexProject/Service45` as the source for the Django setup, template and static-file patterns, color palette, Unfold admin design, and customer-profile page structure. Preserve the useful structure and visual language while using Hamzaban-specific names and behavior.

Useful reference areas in Service45 include:

- `config/settings.py` and `config/admin_setup.py` for Django and Unfold setup.
- `services/templates/services/profile/` for the profile page structure.
- `services/static/services/admin/unfold-custom.css` and `services/static/services/` for admin styling, local assets, and frontend patterns.
- The existing primary teal accent is `#3AA58C`; reuse the Service45 palette and design tokens as the starting point. The current Hamzaban admin theme uses the same Unfold primary scale.

Do not copy Service45 wholesale. Keep its car-service models, migrations, business rules, production configuration, database dumps, uploaded media, `.env` files, and credentials out of Hamzaban. Rebuild domain models, permissions, URLs, and admin registrations for Hamzaban. Never point Hamzaban at a Service45 database.

## Stack and implementation rules

- Use Django and PostgreSQL for server behavior and persistence. Enforce authentication, role checks, and object-level access on the server.
- Render pages with Django templates and use React where client-side interaction needs it. Serve JavaScript, CSS, fonts, icons, images, and Lottie JSON from this project; do not use external CDNs or foreign runtime endpoints.
- Use the existing Service45 palette and component patterns. Keep shared headers, footers, navigation, form controls, and admin patterns consistent.
- Support Persian and RTL layouts. Design mobile-first: turn tables into cards on small screens, put filters in a drawer, show modals as bottom sheets, and keep bottom navigation when it is the primary mobile navigation.
- Check dark and light themes for text and icon contrast, tables, dialogs, filters, forms, dropdowns, borders, and shadows.
- Handle failed requests visibly with short, actionable SweetAlert-style feedback. Cover timeout, validation, unauthorized, forbidden, not found, rate-limit, and server errors; do not fail silently.
- Keep consistent 4xx and 5xx pages, with a light tone, locally served Lottie artwork, and recovery actions such as retry, back, home, or support. Make them usable on mobile and in both themes.
- Require two deliberate confirmations before logging a user out.
- Show every record status as a colored chip in the admin lists, the client app, the therapist app, and list cards. Use the model's Persian label. Waiting statuses are amber (`pending`, `awaiting`, `submitted`, `held`, `unread`). Active statuses are teal (`approved`, `confirmed`, `accepted`, `open`). Booked is blue. Finished and read statuses are muted (`completed`, `read`). Rejected, cancelled, suspended, and refunded statuses are red. Add the same chip, in both themes, when a new status is introduced. In admin, render it with Unfold's label chip.

## Privacy and correctness

Therapy and account information is sensitive. Store only needed data, enforce ownership and role access on the backend, and use fictional records in tests, previews, and screenshots. Keep credentials and private client details out of source control, logs, and error messages.

For booking work, test simultaneous attempts to reserve one slot. For cancellation or rescheduling, verify what both client and therapist see and whether the original slot becomes available again. For frontend and backend changes, agree on request, success, and failure behavior; test the interface against the real local API when available.

## Verification and completion

- Add or update smoke and unit tests for behavior changes. Keep at least 80% coverage for the changed area where the project's coverage setup supports measuring it.
- Run the relevant project checks and tests, then review the diff for unrelated changes. Report exactly what ran and what remains unverified.
- For UI changes, check narrow mobile layouts, Persian/RTL behavior, and both dark and light themes.
- Record start and verification commands here only after confirming they work in this repository. Do not invent commands based on the Service45 reference.
- Do not commit, push, open a pull request, or deploy unless the user requests that action.
