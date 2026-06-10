from django.db import migrations


def ensure_column(apps, schema_editor):
    # ADD COLUMN IF NOT EXISTS is PostgreSQL-only; on SQLite (local dev) the
    # regular AddField migration 0018 already created this column.
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        """
        ALTER TABLE core_userprofile
        ADD COLUMN IF NOT EXISTS last_inactivity_reminded
        TIMESTAMP WITH TIME ZONE NULL;
        """
    )


class Migration(migrations.Migration):
    """
    Re-applies the last_inactivity_reminded column using IF NOT EXISTS in case
    migration 0018 was recorded as applied but the column was never created.
    """

    dependencies = [
        ("core", "0018_add_last_inactivity_reminded"),
    ]

    operations = [
        migrations.RunPython(ensure_column, migrations.RunPython.noop),
    ]
