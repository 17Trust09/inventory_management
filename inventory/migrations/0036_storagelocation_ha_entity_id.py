from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0035_cable_inventoryitem_overview_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="storagelocation",
            name="ha_entity_id",
            field=models.CharField(
                blank=True,
                help_text="Optional: Home-Assistant Entity-ID für LED/Schublade (z. B. light.drawer_a1)",
                max_length=100,
                null=True,
            ),
        ),
    ]
