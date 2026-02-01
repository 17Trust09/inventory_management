from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0059_add_item_comments"),
    ]

    operations = [
        migrations.AddField(
            model_name="itemcomment",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am"),
        ),
    ]
