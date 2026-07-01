# Generated manually – PendingCategoryRequest + PendingTagRequest

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0065_add_active_git_branch'),
    ]

    operations = [
        migrations.CreateModel(
            name='PendingCategoryRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Gewünschter Name')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('approved', models.BooleanField(blank=True, default=None, null=True, verbose_name='Freigegeben')),
                ('reviewed_at', models.DateTimeField(blank=True, null=True, verbose_name='Bearbeitet am')),
                ('requested_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.user', verbose_name='Angefragt von')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_category_requests', to='auth.user', verbose_name='Bearbeitet von')),
            ],
            options={
                'verbose_name': 'Kategorie-Anfrage',
                'verbose_name_plural': 'Kategorie-Anfragen',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PendingTagRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='Gewünschter Name')),
                ('type_name', models.CharField(blank=True, max_length=50, verbose_name='Tag-Typ (optional)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('approved', models.BooleanField(blank=True, default=None, null=True, verbose_name='Freigegeben')),
                ('reviewed_at', models.DateTimeField(blank=True, null=True, verbose_name='Bearbeitet am')),
                ('requested_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.user', verbose_name='Angefragt von')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_tag_requests', to='auth.user', verbose_name='Bearbeitet von')),
            ],
            options={
                'verbose_name': 'Tag-Anfrage',
                'verbose_name_plural': 'Tag-Anfragen',
                'ordering': ['-created_at'],
            },
        ),
    ]
