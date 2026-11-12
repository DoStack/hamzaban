from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("therapy", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="event_key",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="notification",
            name="link",
            field=models.CharField(blank=True, max_length=240),
        ),
    ]
