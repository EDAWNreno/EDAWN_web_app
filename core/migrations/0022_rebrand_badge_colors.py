# Generated for the Northern NV Now rebrand.

from django.db import migrations, models


NEW_BADGE_COLORS = {
    'First Steps': '#6c757d',
    'Making Contact': '#ed7626',
    'Door Knocker': '#00455b',
    'First Visit': '#ed7626',
    'Road Warrior': '#c95718',
    'Ambassador': '#00455b',
    'Veteran': '#198754',
    'Legend': '#dc3545',
}

OLD_BADGE_COLORS = {
    'First Steps': '#6c757d',
    'Making Contact': '#0d6efd',
    'Door Knocker': '#6610f2',
    'First Visit': '#008b99',
    'Road Warrior': '#e67e22',
    'Ambassador': '#014684',
    'Veteran': '#198754',
    'Legend': '#dc3545',
}


def apply_badge_colors(apps, schema_editor):
    Badge = apps.get_model('core', 'Badge')
    for name, color in NEW_BADGE_COLORS.items():
        Badge.objects.filter(name=name).update(color=color)
    Badge.objects.filter(name='Ambassador').update(
        description='Completed 10 company visits. A true Northern NV Now ambassador!'
    )


def restore_badge_colors(apps, schema_editor):
    Badge = apps.get_model('core', 'Badge')
    for name, color in OLD_BADGE_COLORS.items():
        Badge.objects.filter(name=name).update(color=color)
    Badge.objects.filter(name='Ambassador').update(
        description='Completed 10 company visits. A true EDAWN ambassador!'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_merge_migration_branches'),
    ]

    operations = [
        migrations.AlterField(
            model_name='badge',
            name='color',
            field=models.CharField(
                default='#ed7626',
                help_text='Hex color for the badge',
                max_length=7,
            ),
        ),
        migrations.RunPython(apply_badge_colors, restore_badge_colors),
    ]
