import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


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
        self.assertContains(response, "نمای کلی")
        self.assertContains(response, 'data-display-name="لیلا"')
        self.assertContains(response, "client-profile-app")
        self.assertContains(response, 'src="/static/build/client-profile.js"')


class RegistrationTests(TestCase):
    def test_register_page_links_to_login(self):
        response = self.client.get(reverse("register"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ثبت‌نام در هم‌زبان")
        self.assertContains(response, reverse("login"))

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
        profile = self.client.get(reverse("client_profile"))
        self.assertContains(profile, 'data-display-name="لیلا"')

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


class PublicSiteTests(TestCase):
    def test_home_shows_the_landing_sections(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "درمانگر مناسب خود را پیدا کنید")
        self.assertContains(response, "هم‌زبان چیست")
        self.assertContains(response, "۲۴")
        self.assertContains(response, 'id="faq"')
        self.assertContains(response, "زمان‌های صفحهٔ درمانگر قطعی است؟")

    def test_search_filters_the_static_therapist_list(self):
        response = self.client.get(reverse("therapist_list"), {"q": "كودك"})

        self.assertContains(response, "لیلا بهرامی")
        self.assertNotContains(response, "سارا نیک‌فر")
        self.assertContains(response, reverse("therapist_detail", args=["leila-bahrami"]))

    def test_unknown_search_shows_an_empty_state(self):
        response = self.client.get(reverse("therapist_list"), {"q": "نبود"})

        self.assertContains(response, "درمانگری با این جستجو پیدا نشد")
        self.assertNotContains(response, "سارا نیک‌فر")

    def test_therapist_page_shows_sample_schedule(self):
        response = self.client.get(reverse("therapist_detail", args=["sara-nikfar"]))

        self.assertContains(response, "سارا نیک‌فر")
        self.assertContains(response, "زمان‌های آزاد")
        self.assertContains(response, "۱۶:۰۰")
        self.assertContains(response, "این برنامه نمونه است")

    def test_unknown_therapist_is_not_found(self):
        response = self.client.get(reverse("therapist_detail", args=["missing-person"]))

        self.assertEqual(response.status_code, 404)


class VercelDeploymentTests(TestCase):
    def test_vercel_does_not_publish_a_dist_directory(self):
        config = json.loads((settings.BASE_DIR / "vercel.json").read_text(encoding="utf-8"))

        self.assertEqual(config["framework"], "django")
        self.assertEqual(config["buildCommand"], "npm ci && npm run build")
        self.assertNotIn("outputDirectory", config)


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
