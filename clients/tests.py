import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from therapy.factories import make_profile, registration_data
from therapy.models import MoodLog, TherapistProfile


class ClientProfileTests(TestCase):
    def test_anonymous_user_is_sent_to_login(self):
        response = self.client.get(reverse("client_profile"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('client_profile')}",
            fetch_redirect_response=False,
        )

    def test_signed_in_user_sees_the_profile_shell(self):
        user = get_user_model().objects.create_user(
            username="leila",
            password="local-test-password",
            first_name="لیلا",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("client_profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "logout-confirm.js")
        self.assertContains(response, "app-shell")
        self.assertContains(response, "manifest.webmanifest?app=client")
        self.assertNotContains(response, "site-header")
        self.assertNotContains(response, "site-footer")
        self.assertContains(response, 'src="/static/build/app.js"')
        self.assertEqual(self.client.get(reverse("api_me")).json()["name"], "لیلا")

    def test_home_saves_mood_and_account_saves_telegram(self):
        user = get_user_model().objects.create_user(
            username="leila",
            password="local-test-password",
            first_name="لیلا",
            email="leila@example.com",
        )
        self.client.force_login(user)

        home = self.client.get(reverse("api_client_home"))
        self.assertEqual(home.status_code, 200)
        self.assertTrue(home.json()["tasks"])

        saved = self.client.post(
            reverse("api_client_home"),
            data='{"emoji": "😊", "word": "آرام"}',
            content_type="application/json",
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(MoodLog.objects.get(client=user).word, "آرام")

        page = self.client.get(reverse("client_account"))
        self.assertContains(page, "app-shell")
        account = self.client.post(
            reverse("api_client_account"),
            data='{"first_name": "لیلا", "email": "leila@example.com", "telegram_username": "@hamzaban_user"}',
            content_type="application/json",
        )
        self.assertEqual(account.status_code, 200)
        user.client_profile.refresh_from_db()
        self.assertEqual(user.client_profile.telegram_username, "hamzaban_user")


class LogoutTests(TestCase):
    def test_client_and_therapist_profiles_can_log_out(self):
        client = get_user_model().objects.create_user(username="leila", password="Safe-pass-48", first_name="لیلا")
        self.client.force_login(client)
        profile = self.client.get(reverse("client_profile"))
        self.assertContains(profile, "logout-confirm.js")
        logged_out = self.client.post(reverse("logout"))
        self.assertRedirects(logged_out, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)

        therapist = make_profile(status=TherapistProfile.Status.APPROVED)
        self.client.force_login(therapist.user)
        panel = self.client.get(reverse("therapist_home"))
        self.assertContains(panel, "logout-confirm.js")
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)


class RegistrationTests(TestCase):
    def test_register_page_links_to_login(self):
        response = self.client.get(reverse("register"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'src="/static/build/app.js"')
        self.assertIn("/accounts/login/", (settings.BASE_DIR / "static/build/app.js").read_text(encoding="utf-8"))

    def test_valid_registration_creates_client_and_opens_profile(self):
        response = self.client.post(
            reverse("register"),
            {
                "first_name": "لیلا",
                "username": "leila",
                "email": "leila@example.com",
                "password1": "Safe-pass-48",
                "password2": "Safe-pass-48",
            },
        )

        self.assertRedirects(response, reverse("client_profile"))
        user = get_user_model().objects.get(username="leila")
        self.assertEqual(user.first_name, "لیلا")
        self.assertEqual(user.email, "leila@example.com")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password("Safe-pass-48"))
        self.assertEqual(self.client.get(reverse("api_me")).json()["name"], "لیلا")

    def test_duplicate_username_or_email_is_rejected(self):
        get_user_model().objects.create_user(
            username="leila",
            email="leila@example.com",
            password="Safe-pass-48",
        )
        payload = {
            "first_name": "سارا",
            "username": "leila",
            "email": "LEILA@example.com",
            "password1": "Safe-pass-48",
            "password2": "Safe-pass-48",
        }

        response = self.client.post(reverse("register"), payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "form-error")
        self.assertEqual(get_user_model().objects.count(), 1)

        payload["username"] = "sara"
        response = self.client.post(reverse("register"), payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "این ایمیل قبلاً ثبت شده است.")
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_mismatched_passwords_do_not_create_a_user(self):
        response = self.client.post(
            reverse("register"),
            {
                "first_name": "لیلا",
                "username": "leila",
                "email": "leila@example.com",
                "password1": "Safe-pass-48",
                "password2": "Other-pass-48",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "form-error")
        self.assertFalse(get_user_model().objects.filter(username="leila").exists())

    def test_validation_messages_stay_persian_for_english_browsers(self):
        response = self.client.post(reverse("register"), {}, HTTP_ACCEPT_LANGUAGE="en")

        self.assertContains(response, "این فیلد لازم است.")
        self.assertNotContains(response, "This field is required.")

    def test_signed_in_user_skips_registration(self):
        user = get_user_model().objects.create_user(username="leila", password="Safe-pass-48")
        self.client.force_login(user)

        response = self.client.get(reverse("register"))

        self.assertRedirects(response, reverse("client_profile"))


class TherapistRegistrationTests(TestCase):
    def test_landing_is_a_static_page_with_a_register_button(self):
        response = self.client.get(reverse("therapist_landing"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'src="/static/build/app.js"')
        self.assertIn(reverse("therapist_register"), (settings.BASE_DIR / "static/build/app.js").read_text(encoding="utf-8"))

    def test_register_page_is_separate_from_the_client_form(self):
        response = self.client.get(reverse("therapist_register"))

        self.assertEqual(response.status_code, 200)
        script = (settings.BASE_DIR / "static/build/app.js").read_text(encoding="utf-8")
        self.assertContains(response, 'src="/static/build/app.js"')
        self.assertIn("ثبت‌نام درمانگر", script)
        self.assertIn("فایل مجوز", script)
        self.assertIn(reverse("register"), script)
        self.assertIn(reverse("login"), script)

    def test_valid_registration_creates_a_therapist_and_opens_the_panel(self):
        payload = registration_data()
        payload["license_file"] = SimpleUploadedFile("license.pdf", b"%PDF-1.4", content_type="application/pdf")
        response = self.client.post(reverse("therapist_register"), payload)

        self.assertRedirects(response, reverse("therapist_home"))
        user = get_user_model().objects.get(username="sara")
        self.assertTrue(user.groups.filter(name="therapist").exists())
        self.assertFalse(user.is_staff)
        self.assertEqual(user.therapist_profile.status, TherapistProfile.Status.PENDING)
        self.assertEqual(user.therapist_profile.display_name, "سارا نیک‌فر")
        profile = self.client.get(reverse("client_profile"))
        self.assertRedirects(profile, reverse("therapist_home"))

    def test_signed_in_client_skips_therapist_registration(self):
        user = get_user_model().objects.create_user(username="leila", password="Safe-pass-48")
        self.client.force_login(user)

        response = self.client.get(reverse("therapist_register"))

        self.assertRedirects(response, reverse("client_profile"))

    def test_client_login_still_opens_the_profile(self):
        get_user_model().objects.create_user(username="leila", password="Safe-pass-48")

        response = self.client.post(
            reverse("login"),
            {"username": "leila", "password": "Safe-pass-48"},
        )

        self.assertRedirects(response, reverse("client_profile"))

    def test_therapist_login_opens_the_landing_page(self):
        user = get_user_model().objects.create_user(username="sara", password="Safe-pass-48")
        user.groups.create(name="therapist")

        response = self.client.post(
            reverse("login"),
            {"username": "sara", "password": "Safe-pass-48"},
        )

        self.assertRedirects(response, reverse("therapist_home"))


class PublicSiteTests(TestCase):
    def test_home_shows_the_landing_sections(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'src="/static/build/app.js"')
        payload = self.client.get(reverse("api_home")).json()
        self.assertIn("۲۴", [item["value"] for item in payload["stats"]])
        self.assertTrue(any("زمان‌های صفحهٔ درمانگر قطعی است؟" in item["question"] for item in payload["faqs"]))
        self.assertContains(response, "manifest.webmanifest?app=client")
        landing = self.client.get(reverse("therapist_landing"))
        self.assertContains(landing, "manifest.webmanifest?app=therapist")
        self.assertContains(landing, "site-header")
        therapist = self.client.get(reverse("api_home"), {"app": "therapist"}).json()
        self.assertEqual([item["title"] for item in therapist["steps"]], ["ثبت‌نام", "بررسی", "ساعت‌ها", "جلسه‌ها"])
        self.assertIn("۲ روز", [item["value"] for item in therapist["stats"]])

    def test_search_filters_approved_therapists_with_open_slots(self):
        make_profile(
            username="leila",
            display_name="لیلا بهرامی",
            specialties=["کودک و نوجوان"],
            status=TherapistProfile.Status.APPROVED,
            with_hours=True,
            slug="leila-bahrami",
        )
        make_profile(
            username="sara",
            display_name="سارا نیک‌فر",
            specialties=["اضطراب"],
            status=TherapistProfile.Status.APPROVED,
            with_hours=True,
            slug="sara-nikfar",
        )

        response = self.client.get(reverse("api_therapists"), {"q": "كودك"})
        names = [item["name"] for item in response.json()["therapists"]]
        slugs = [item["slug"] for item in response.json()["therapists"]]

        self.assertIn("لیلا بهرامی", names)
        self.assertNotIn("سارا نیک‌فر", names)
        self.assertIn("leila-bahrami", slugs)

    def test_persian_slug_can_be_linked_from_the_list(self):
        profile = make_profile(
            username="terapist",
            display_name="تراپیست",
            status=TherapistProfile.Status.APPROVED,
            with_hours=True,
            slug="تراپیست",
        )
        profile.photo = SimpleUploadedFile("face.png", b"\x89PNG\r\n", content_type="image/png")
        profile.save(update_fields=["photo"])

        listed = self.client.get(reverse("api_therapists")).json()["therapists"]
        match = next(item for item in listed if item["slug"] == "تراپیست")

        self.assertEqual(match["photo"], reverse("therapist_photo", args=["تراپیست"]))
        self.assertEqual(self.client.get(reverse("therapist_detail", args=["تراپیست"])).status_code, 200)

    def test_unknown_search_shows_an_empty_state(self):
        response = self.client.get(reverse("api_therapists"), {"q": "نبود"})

        self.assertEqual(response.json()["therapists"], [])

    def test_therapist_page_shows_open_slots(self):
        make_profile(
            username="sara",
            display_name="سارا نیک‌فر",
            status=TherapistProfile.Status.APPROVED,
            with_hours=True,
            slug="sara-nikfar",
        )

        response = self.client.get(reverse("api_therapist_detail", args=["sara-nikfar"]))
        payload = response.json()
        times = [slot["time"] for day in payload["days"] for slot in day["slots"]]

        self.assertEqual(payload["therapist"]["name"], "سارا نیک‌فر")
        self.assertIn("12:00", times)
        self.assertContains(self.client.get(reverse("therapist_detail", args=["sara-nikfar"])), 'src="/static/build/app.js"')

    def test_unknown_therapist_is_not_found(self):
        response = self.client.get(reverse("therapist_detail", args=["missing-person"]))

        self.assertEqual(response.status_code, 404)


class FaviconTests(TestCase):
    def test_favicon_is_used_on_the_site_and_in_the_admin(self):
        icon = self.client.get(reverse("favicon"))
        self.assertRedirects(icon, "/static/favicon.svg", fetch_redirect_response=False)

        for url in (reverse("home"), reverse("therapist_landing"), reverse("admin:login")):
            response = self.client.get(url)
            self.assertContains(response, 'href="/static/favicon.svg"')


class AdminDataTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="admin",
            password="Safe-pass-48",
            is_staff=True,
        )

    def test_anonymous_visitor_cannot_open_the_data_list(self):
        response = self.client.get(reverse("admin:data_index"))

        self.assertRedirects(
            response,
            f"{reverse('admin:login')}?next={reverse('admin:data_index')}",
            fetch_redirect_response=False,
        )

    def test_staff_sees_the_roadmap_and_can_open_it(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse("admin:data_index"))

        self.assertContains(response, "data")
        self.assertContains(response, "Hamzaban_roadmap_v1.html")
        opened = self.client.get(reverse("admin:data_file", args=["Hamzaban_roadmap_v1.html"]))
        self.assertEqual(opened["Content-Type"], "text/html; charset=utf-8")
        self.assertContains(opened, "Hamzaban Roadmap v1")

    def test_a_file_outside_the_data_folder_is_not_served(self):
        self.client.force_login(self.staff)

        missing = self.client.get(reverse("admin:data_file", args=["settings.py"]))
        escaped = self.client.get(reverse("admin:data_file", args=[".."]))

        self.assertEqual(missing.status_code, 404)
        self.assertEqual(escaped.status_code, 404)

    def test_client_account_cannot_open_data(self):
        user = get_user_model().objects.create_user(username="leila", password="Safe-pass-48")
        self.client.force_login(user)

        response = self.client.get(reverse("admin:data_index"))

        self.assertRedirects(
            response,
            f"{reverse('admin:login')}?next={reverse('admin:data_index')}",
            fetch_redirect_response=False,
        )


class AdminTableTests(TestCase):
    def test_superuser_can_open_every_database_table(self):
        get_user_model().objects.create_superuser(
            username="root",
            email="root@example.com",
            password="Safe-pass-48",
        )
        self.client.force_login(get_user_model().objects.get(username="root"))
        names = (
            "auth_user",
            "auth_group",
            "auth_permission",
            "contenttypes_contenttype",
            "sessions_session",
            "admin_logentry",
            "auth_user_groups",
            "auth_user_user_permissions",
            "auth_group_permissions",
        )

        for name in names:
            response = self.client.get(reverse(f"admin:{name}_changelist"))
            self.assertEqual(response.status_code, 200, name)

        index = self.client.get(reverse("admin:index"))
        self.assertContains(index, "اجازه‌ها")
        self.assertContains(index, "نشست‌ها")
        self.assertTrue(settings.UNFOLD["SIDEBAR"]["show_all_applications"])


class VercelDeploymentTests(TestCase):
    def test_vercel_does_not_publish_a_dist_directory(self):
        config = json.loads((settings.BASE_DIR / "vercel.json").read_text(encoding="utf-8"))

        self.assertEqual(config["framework"], "django")
        self.assertEqual(config["buildCommand"], "npm ci && npm run build")
        self.assertNotIn("outputDirectory", config)
        project = (settings.BASE_DIR / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("[project]", project)
        self.assertIn("Django==5.2", project)
        self.assertIn("psycopg2-binary>=2.9", project)
        self.assertIn("django-unfold>=0.43", project)
        links = [
            item["link"]
            for section in settings.UNFOLD["SIDEBAR"]["navigation"]
            for item in section["items"]
        ]
        self.assertTrue(all(isinstance(link, str) for link in links))
        self.assertTrue(all(isinstance(path, str) for path in settings.UNFOLD["STYLES"]))
        self.assertTrue(all(isinstance(path, str) for path in settings.UNFOLD["SCRIPTS"]))

    def test_django_prefers_the_direct_neon_connection(self):
        from config.settings import preferred_database_url

        selected = preferred_database_url(
            {
                "DATABASE_URL": "postgres://pooled.example/hamzaban",
                "DATABASE_URL_UNPOOLED": "postgres://direct.example/hamzaban",
            }
        )

        self.assertEqual(selected, "postgres://direct.example/hamzaban")


class LocalAssetTests(TestCase):
    def test_public_pages_keep_styles_and_scripts_on_this_site(self):
        response = self.client.get(reverse("login"))
        html = response.content.decode()

        self.assertContains(response, 'href="/static/css/site.css"')
        self.assertContains(response, 'src="/static/js/theme.js"')
        self.assertNotIn("fonts.googleapis.com", html)
        self.assertNotIn("cdn.", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)

        static_dir = settings.BASE_DIR / "static"
        for relative_path in ("css/site.css", "css/admin.css", "css/fonts.css"):
            stylesheet = (static_dir / relative_path).read_text(encoding="utf-8")
            self.assertIn('"پیدا"', stylesheet)
            self.assertNotIn("http://", stylesheet)
            self.assertNotIn("https://", stylesheet)
            self.assertNotIn("Vazirmatn", stylesheet)
