from django.db import migrations


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
        migrations.RunSQL(
            sql="""
                ALTER TABLE core_userprofile
                    ADD COLUMN IF NOT EXISTS last_inactivity_reminded TIMESTAMP WITH TIME ZONE,
                    ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20) NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS sms_reminders_enabled BOOLEAN NOT NULL DEFAULT FALSE;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
