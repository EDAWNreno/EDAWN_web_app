from django.db import migrations


def ensure_columns(apps, schema_editor):
    # ADD COLUMN IF NOT EXISTS is PostgreSQL-only; on SQLite (local dev) the
    # regular AddField migrations 0018/0019 already created these columns.
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        """
        ALTER TABLE core_userprofile
            ADD COLUMN IF NOT EXISTS last_inactivity_reminded TIMESTAMP WITH TIME ZONE,
            ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20) NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS sms_reminders_enabled BOOLEAN NOT NULL DEFAULT FALSE;
        """
    )


class Migration(migrations.Migration):
    """
    Safety migration: adds the three new UserProfile columns using IF NOT EXISTS
    so the statements are idempotent. Guards against deployments where 0018/0019
    were recorded in django_migrations but the DDL never reached the DB.
    """

    dependencies = [
        ("core", "0019_add_sms_fields_to_userprofile"),
    ]

    operations = [
        migrations.RunPython(ensure_columns, migrations.RunPython.noop),
    ]
