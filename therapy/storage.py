from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class DatabaseStorage(Storage):
    """Keep uploaded files in Postgres. The Vercel function disk is read-only."""

    def _open(self, name, mode="rb"):
        from therapy.models import StoredFile

        stored = StoredFile.objects.get(name=name)
        return ContentFile(bytes(stored.content))

    def _save(self, name, content):
        from therapy.models import StoredFile

        StoredFile.objects.update_or_create(name=name, defaults={"content": content.read()})
        return name

    def exists(self, name):
        from therapy.models import StoredFile

        return StoredFile.objects.filter(name=name).exists()

    def delete(self, name):
        from therapy.models import StoredFile

        StoredFile.objects.filter(name=name).delete()

    def size(self, name):
        opened = self._open(name)
        return opened.size

    def url(self, name):
        return ""
