from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Max, Q
from django.utils import timezone

from core.emails import notify_staff_volunteer_overdue, notify_volunteer_inactivity
from core.models import Assignment, UserProfile


class Command(BaseCommand):
    help = 'Email volunteers inactive 30+ days (F-15) and alert staff at 45+ days (F-16)'

    def handle(self, *args, **options):
        now       = timezone.now()
        cutoff_30 = now - timedelta(days=30)
        cutoff_45 = now - timedelta(days=45)

        # Volunteers with at least one active assignment, annotated with last visit
        candidates = (
            User.objects
            .filter(is_active=True, is_staff=False, assignments__status=Assignment.STATUS_ACTIVE)
            .annotate(last_visit=Max('assignments__visit_notes__visit_date'))
            .filter(Q(last_visit__lt=cutoff_30) | Q(last_visit__isnull=True))
            .distinct()
            .select_related('profile')
        )

        reminded = 0
        alerted  = 0

        for vol in candidates:
            if not vol.email:
                continue

            active = list(
                Assignment.objects
                .filter(volunteer=vol, status=Assignment.STATUS_ACTIVE)
                .select_related('company')
            )

            if vol.last_visit:
                days_inactive = (now - vol.last_visit).days
            else:
                first = Assignment.objects.filter(volunteer=vol).order_by('assigned_date').first()
                days_inactive = (now - first.assigned_date).days if first else 0

            # F-15: remind the volunteer at 30+ days
            notify_volunteer_inactivity(vol, active, days_inactive)
            reminded += 1

            # F-16: alert staff at 45+ days, but only once per inactive period
            if days_inactive >= 45:
                profile = getattr(vol, 'profile', None)
                if profile is None:
                    profile, _ = UserProfile.objects.get_or_create(user=vol)
                if not profile.last_inactivity_notified:
                    notify_staff_volunteer_overdue(vol, days_inactive)
                    profile.last_inactivity_notified = now
                    profile.save(update_fields=['last_inactivity_notified'])
                    alerted += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Done — {reminded} volunteer reminder(s) sent, {alerted} staff alert(s) sent.'
            )
        )
