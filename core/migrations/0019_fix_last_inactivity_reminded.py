from django.db import migrations


class Migration(migrations.Migration):
    """
    Re-applies the last_inactivity_reminded column using IF NOT EXISTS in case
    migration 0018 was recorded as applied but the column was never created.
    """

    dependencies = [
        ("core", "0018_add_last_inactivity_reminded"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE core_userprofile
                ADD COLUMN IF NOT EXISTS last_inactivity_reminded
                TIMESTAMP WITH TIME ZONE NULL;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
