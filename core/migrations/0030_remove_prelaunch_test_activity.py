from django.db import migrations
from django.db.models import Q


def remove_prelaunch_test_activity(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Assignment = apps.get_model("core", "Assignment")
    Company = apps.get_model("core", "Company")
    Message = apps.get_model("core", "Message")
    Reply = apps.get_model("core", "Reply")
    VisitNote = apps.get_model("core", "VisitNote")

    test_users = User.objects.filter(
        Q(first_name__iexact="Daniel", last_name__iexact="Smith")
        | Q(email__iexact="daniel@northernnvnow.com")
        | Q(username__icontains="test")
        | Q(first_name__icontains="test")
        | Q(last_name__icontains="test")
    )
    test_user_ids = list(test_users.values_list("id", flat=True))

    test_visits = VisitNote.objects.filter(visited_by_id__in=test_user_ids)
    affected_assignment_ids = list(
        test_visits.values_list("assignment_id", flat=True).distinct()
    )
    affected_company_ids = list(
        Assignment.objects.filter(id__in=affected_assignment_ids)
        .values_list("company_id", flat=True)
        .distinct()
    )

    message_count = Message.objects.count()
    reply_count = Reply.objects.count()
    visit_count = test_visits.count()

    # Replies cascade from their parent messages.
    Message.objects.all().delete()
    test_visits.delete()

    reset_assignments = 0
    for assignment in Assignment.objects.filter(id__in=affected_assignment_ids):
        has_remaining_visit = VisitNote.objects.filter(
            assignment_id=assignment.id
        ).exists()
        if not has_remaining_visit and assignment.status == "completed":
            Assignment.objects.filter(id=assignment.id).update(
                status="active",
                completed_date=None,
            )
            reset_assignments += 1

    reset_companies = 0
    for company in Company.objects.filter(
        id__in=affected_company_ids,
        is_archived=False,
        status="visited",
    ):
        has_remaining_visit = VisitNote.objects.filter(
            assignment__company_id=company.id
        ).exists()
        if has_remaining_visit:
            continue

        has_active_assignment = Assignment.objects.filter(
            company_id=company.id,
            status="active",
        ).exists()
        Company.objects.filter(id=company.id).update(
            status="assigned" if has_active_assignment else "unassigned"
        )
        reset_companies += 1

    print(
        "Prelaunch cleanup complete: "
        f"{message_count} messages, {reply_count} replies, "
        f"{visit_count} visits removed; "
        f"{reset_assignments} assignments and {reset_companies} companies reset."
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0029_backfill_salesforce_last_visit_dates"),
    ]

    operations = [
        migrations.RunPython(
            remove_prelaunch_test_activity,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
