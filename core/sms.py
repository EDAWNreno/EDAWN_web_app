from django.conf import settings


def _client():
    from twilio.rest import Client
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def _enabled():
    return bool(
        getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        and getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        and getattr(settings, 'TWILIO_FROM_NUMBER', None)
    )


def send_sms(to, body):
    if not _enabled() or not to:
        return
    try:
        _client().messages.create(
            to=to,
            from_=settings.TWILIO_FROM_NUMBER,
            body=body,
        )
    except Exception:
        pass


def notify_volunteer_inactivity_sms(volunteer, active_assignments, days_since_visit):
    phone = getattr(getattr(volunteer, 'profile', None), 'phone_number', None)
    if not phone:
        return
    first_name = volunteer.first_name or volunteer.username
    company_names = ', '.join(a.company.name for a in active_assignments[:3])
    suffix = '...' if len(active_assignments) > 3 else ''
    send_sms(
        phone,
        f"Hi {first_name}, it's been {days_since_visit} days since your last Business Builders visit. "
        f"Your active companies: {company_names}{suffix}. "
        f"Log in at {settings.SITE_URL} to plan your next visit."
    )
