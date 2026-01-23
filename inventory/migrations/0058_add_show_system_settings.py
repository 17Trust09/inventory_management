from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0057_add_system_scaling_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="globalsettings",
            name="show_system_settings",
            field=models.BooleanField(
                default=True,
                verbose_name="System-Einstellungen anzeigen",
            ),
        ),
    ]
