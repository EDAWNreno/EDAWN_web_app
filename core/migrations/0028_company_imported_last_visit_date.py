from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0027_company_browse_visibility'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='imported_last_visit_date',
            field=models.DateField(
                blank=True,
                db_index=True,
                help_text='Most recent known visit imported from a prior system or CSV.',
                null=True,
            ),
        ),
    ]
