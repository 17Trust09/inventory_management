from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0058_add_show_system_settings"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ItemComment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.TextField(verbose_name="Kommentar")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="item_comments",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Autor",
                    ),
                ),
                (
                    "item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="comments",
                        to="inventory.inventoryitem",
                        verbose_name="Artikel",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="itemcomment",
            index=models.Index(fields=["item", "-created_at"], name="inventory_i_item_id_e2a9b0_idx"),
        ),
    ]
