from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, default_storage
from django.core.management.base import BaseCommand, CommandError

from config.settings import file_storage
from therapy.models import StoredFile


class Command(BaseCommand):
    help = "Copy uploaded files from this computer and the database into R2."

    def handle(self, *args, **options):
        if file_storage() != "r2":
            raise CommandError(
                "Set R2_ACCOUNT_ID, R2_BUCKET_NAME, R2_ACCESS_KEY_ID, and R2_SECRET_ACCESS_KEY first."
            )
        copied = 0
        copied += self._copy_local_media()
        copied += self._copy_database_files()
        self.stdout.write(f"Copied {copied} files to R2.")

    def _copy_local_media(self):
        root = Path(settings.MEDIA_ROOT)
        if not root.is_dir():
            return 0
        local = FileSystemStorage(location=root)
        copied = 0
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            name = path.relative_to(root).as_posix()
            if default_storage.exists(name):
                continue
            with local.open(name, "rb") as handle:
                default_storage.save(name, ContentFile(handle.read()))
            copied += 1
        return copied

    def _copy_database_files(self):
        copied = 0
        for stored in StoredFile.objects.order_by("name"):
            if not stored.name or default_storage.exists(stored.name):
                continue
            default_storage.save(stored.name, ContentFile(bytes(stored.content)))
            copied += 1
        return copied
