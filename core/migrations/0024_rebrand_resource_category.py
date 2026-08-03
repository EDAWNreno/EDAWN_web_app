from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_ensure_badge_definitions'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resource',
            name='category',
            field=models.CharField(
                choices=[
                    ('visit_script', 'Visit Script'),
                    ('snapshot_form', 'Company Snapshot Form'),
                    ('workforce_guide', 'Workforce Guide'),
                    ('value_prop', 'Northern NV Now Value Prop'),
                    ('other', 'Other'),
                ],
                default='other',
                max_length=30,
            ),
        ),
    ]
