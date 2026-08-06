from django.db import migrations
from django.utils import timezone


def unassign_ds1044_companies(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Assignment = apps.get_model("core", "Assignment")
    Company = apps.get_model("core", "Company")

    user_ids = list(
        User.objects.filter(email__iexact="ds1044@gmail.com")
        .values_list("id", flat=True)
    )
    active_assignments = list(
        Assignment.objects.filter(
            volunteer_id__in=user_ids,
            status="active",
        )
    )

    unassigned_at = timezone.now()
    released_companies = 0
    for assignment in active_assignments:
        Assignment.objects.filter(id=assignment.id).update(
            status="unassigned",
            unassigned_at=unassigned_at,
            unassigned_by=None,
        )

        has_other_active_assignment = Assignment.objects.filter(
            company_id=assignment.company_id,
            status="active",
        ).exists()
        if not has_other_active_assignment:
            Company.objects.filter(id=assignment.company_id).update(
                status="unassigned",
                updated_at=unassigned_at,
            )
            released_companies += 1

    print(
        "Daniel assignment cleanup complete: "
        f"{len(active_assignments)} active assignments unassigned; "
        f"{released_companies} companies returned to the unassigned pool."
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0030_remove_prelaunch_test_activity"),
    ]

    operations = [
        migrations.RunPython(
            unassign_ds1044_companies,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
