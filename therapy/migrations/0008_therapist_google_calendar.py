from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("therapy", "0007_client_phone"),
    ]

    operations = [
        migrations.AddField(
            model_name="therapistprofile",
            name="google_email",
            field=models.EmailField(blank=True, max_length=254, verbose_name="ایمیل گوگل"),
        ),
        migrations.AddField(
            model_name="therapistprofile",
            name="google_refresh_token",
            field=models.TextField(blank=True, verbose_name="توکن تقویم"),
        ),
    ]
