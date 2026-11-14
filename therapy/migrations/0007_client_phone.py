from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("therapy", "0006_therapist_review_queue"),
    ]

    operations = [
        migrations.AddField(
            model_name="clientprofile",
            name="phone",
            field=models.CharField(blank=True, max_length=20, verbose_name="شماره تماس"),
        ),
    ]
