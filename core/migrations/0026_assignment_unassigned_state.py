from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_company_archiving'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='assignment',
            name='unassigned_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='assignment',
            name='unassigned_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='assignments_unassigned',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='assignment',
            name='status',
            field=models.CharField(
                choices=[
                    ('active', 'Active'),
                    ('completed', 'Completed'),
                    ('lost', 'Lost'),
                    ('unassigned', 'Unassigned'),
                ],
                db_index=True,
                default='active',
                max_length=20,
            ),
        ),
    ]
