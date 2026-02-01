from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0060_add_item_comment_updated_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="globalsettings",
            name="enable_user_overview_requests",
            field=models.BooleanField(
                default=False,
                verbose_name="Dashboard-Anfragen durch Benutzer erlauben",
            ),
        ),
        migrations.AddField(
            model_name="overview",
            name="requested_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="requested_overviews",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Angefragt von",
            ),
        ),
    ]
