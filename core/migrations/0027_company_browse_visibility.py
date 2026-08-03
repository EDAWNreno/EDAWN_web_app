from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0026_assignment_unassigned_state'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='is_browse_visible',
            field=models.BooleanField(
                db_index=True,
                default=True,
                help_text='Show this company in Browse Companies when it is active and unassigned.',
            ),
        ),
    ]
