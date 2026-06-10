from django.db import migrations


class Migration(migrations.Migration):
    """
    Merge migration: 0019_fix_last_inactivity_reminded and the SMS branch
    (0019_add_sms_fields -> 0020_ensure_userprofile_columns) both branched
    off 0018, leaving two leaf nodes that made `migrate` abort with
    "Conflicting migrations detected" on every deploy.
    """

    dependencies = [
        ("core", "0019_fix_last_inactivity_reminded"),
        ("core", "0020_ensure_userprofile_columns"),
    ]

    operations = []
