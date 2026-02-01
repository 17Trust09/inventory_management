from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0050_add_global_feature_toggles"),
    ]

    operations = [
        migrations.AddField(
            model_name="globalsettings",
            name="enable_item_history",
            field=models.BooleanField(
                default=True,
                verbose_name="Verlauf & Timeline im Item-Edit anzeigen",
            ),
        ),
        migrations.AddField(
            model_name="globalsettings",
            name="enable_item_move",
            field=models.BooleanField(
                default=True,
                verbose_name="Item in anderes Dashboard verschieben erlauben",
            ),
        ),
    ]
