from django.db import migrations


BADGES = [
    {
        'name': 'Certified Business Builder Volunteer',
        'description': (
            'Awarded to volunteers who have completed at least one company visit '
            'in each of the last 3 consecutive calendar months.'
        ),
        'icon': 'bi-patch-check-fill',
        'color': '#014684',
        'criteria_type': 'manual',
        'criteria_value': 0,
        'sort_order': 0,
    },
    {
        'name': 'First Steps',
        'description': 'Received your first company assignment.',
        'icon': 'bi-flag-fill',
        'color': '#6c757d',
        'criteria_type': 'assignments_received',
        'criteria_value': 1,
        'sort_order': 1,
    },
    {
        'name': 'Making Contact',
        'description': 'Logged your first contact attempt.',
        'icon': 'bi-telephone-fill',
        'color': '#ed7626',
        'criteria_type': 'contact_attempts',
        'criteria_value': 1,
        'sort_order': 2,
    },
    {
        'name': 'Door Knocker',
        'description': 'Logged 10 contact attempts. Persistence pays off!',
        'icon': 'bi-door-open-fill',
        'color': '#00455b',
        'criteria_type': 'contact_attempts',
        'criteria_value': 10,
        'sort_order': 3,
    },
    {
        'name': 'First Visit',
        'description': 'Completed your first company visit.',
        'icon': 'bi-star-fill',
        'color': '#ed7626',
        'criteria_type': 'visits_completed',
        'criteria_value': 1,
        'sort_order': 4,
    },
    {
        'name': 'Road Warrior',
        'description': "Completed 5 company visits. You're on a roll!",
        'icon': 'bi-car-front-fill',
        'color': '#c95718',
        'criteria_type': 'visits_completed',
        'criteria_value': 5,
        'sort_order': 5,
    },
    {
        'name': 'Ambassador',
        'description': 'Completed 10 company visits. A true Northern NV Now ambassador!',
        'icon': 'bi-award-fill',
        'color': '#00455b',
        'criteria_type': 'visits_completed',
        'criteria_value': 10,
        'sort_order': 6,
    },
    {
        'name': 'Veteran',
        'description': 'Completed 25 company visits. Legendary dedication!',
        'icon': 'bi-shield-fill-check',
        'color': '#198754',
        'criteria_type': 'visits_completed',
        'criteria_value': 25,
        'sort_order': 7,
    },
    {
        'name': 'Legend',
        'description': 'Completed 50 company visits. Hall of fame material!',
        'icon': 'bi-gem',
        'color': '#dc3545',
        'criteria_type': 'visits_completed',
        'criteria_value': 50,
        'sort_order': 8,
    },
]


def ensure_badges_and_awards(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Assignment = apps.get_model('core', 'Assignment')
    Badge = apps.get_model('core', 'Badge')
    ContactAttempt = apps.get_model('core', 'ContactAttempt')
    UserBadge = apps.get_model('core', 'UserBadge')
    UserProfile = apps.get_model('core', 'UserProfile')

    badges_by_name = {}
    for data in BADGES:
        badge, _ = Badge.objects.update_or_create(
            name=data['name'],
            defaults={
                'description': data['description'],
                'icon': data['icon'],
                'color': data['color'],
                'criteria_type': data['criteria_type'],
                'criteria_value': data['criteria_value'],
                'sort_order': data['sort_order'],
            },
        )
        badges_by_name[badge.name] = badge

    auto_badges = [
        badge for badge in badges_by_name.values()
        if badge.criteria_type != 'manual' and badge.criteria_value > 0
    ]

    for user in User.objects.all():
        stats = {
            'assignments_received': Assignment.objects.filter(volunteer_id=user.id).count(),
            'contact_attempts': ContactAttempt.objects.filter(attempted_by_id=user.id).count(),
            'visits_completed': Assignment.objects.filter(
                volunteer_id=user.id,
                status='completed',
            ).count(),
        }
        for badge in auto_badges:
            if stats.get(badge.criteria_type, 0) >= badge.criteria_value:
                UserBadge.objects.get_or_create(user_id=user.id, badge_id=badge.id)

    bbv_badge = badges_by_name.get('Certified Business Builder Volunteer')
    if bbv_badge:
        for profile in UserProfile.objects.filter(bbv_certified=True):
            UserBadge.objects.get_or_create(user_id=profile.user_id, badge_id=bbv_badge.id)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_rebrand_badge_colors'),
    ]

    operations = [
        migrations.RunPython(ensure_badges_and_awards, migrations.RunPython.noop),
    ]
