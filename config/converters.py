class UnicodeSlugConverter:
    """Slug converter that keeps Persian and other Unicode letters."""

    regex = r"[-\w]+"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value
