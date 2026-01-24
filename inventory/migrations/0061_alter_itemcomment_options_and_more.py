from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0060_add_item_comment_updated_at"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="itemcomment",
            options={"ordering": ["-updated_at", "-created_at"]},
        ),
    ]
