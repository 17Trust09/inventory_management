from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0042_storagelocation_nfc_base_choice"),
    ]

    operations = [
        migrations.AddField(
            model_name="overview",
            name="enable_quick_adjust",
            field=models.BooleanField(default=False, verbose_name="Schnellbestand +/- erlauben"),
        ),
    ]
