from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("therapy", "0008_therapist_google_calendar"),
    ]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="google_event_id",
            field=models.CharField(blank=True, max_length=256, verbose_name="رویداد گوگل"),
        ),
    ]
