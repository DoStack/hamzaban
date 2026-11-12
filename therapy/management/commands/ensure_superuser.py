import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the production superuser from DJANGO_SUPERUSER_* environment variables."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
        if not username or not password:
            self.stdout.write("Superuser settings are empty, so no admin was created.")
            return
        User = get_user_model()
        user = User.objects.filter(username=username).first()
        if user is None:
            User.objects.create_superuser(username, email, password)
            self.stdout.write("Superuser created.")
            return
        user.is_staff = True
        user.is_superuser = True
        if email:
            user.email = email
        if not user.has_usable_password():
            user.set_password(password)
        user.save()
        self.stdout.write("Superuser already exists.")
