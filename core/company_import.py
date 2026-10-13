from datetime import datetime
import re

from django.core.exceptions import ValidationError
from django.core.validators import validate_email


NUMBERED_CONTACT_RE = re.compile(r'^contact_(\d+)_(name|title|email|phone)$')


CSV_FIELD_MAP = {
    'name': 'name',
    'address': 'address',
    'city': 'city',
    'state': 'state',
    'zip': 'zip_code',
    'zip_code': 'zip_code',
    'phone': 'phone',
    'email': 'email',
    'website': 'website',
    'industry': 'industry',
    'contact_name': 'primary_contact_name',
    'primary_contact_name': 'primary_contact_name',
    'contact_title': 'primary_contact_title',
    'primary_contact_title': 'primary_contact_title',
    'notes': 'notes',
}


def company_data_from_csv_row(row):
    data = {}
    for csv_column, model_field in CSV_FIELD_MAP.items():
        value = (row.get(csv_column) or '').strip()
        if value:
            data[model_field] = value

    raw_last_visit = (
        (row.get('last_visit_date') or '').strip()
        or (row.get('last_visit') or '').strip()
    )
    if raw_last_visit:
        parsed_date = None
        for date_format in ('%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y'):
            try:
                parsed_date = datetime.strptime(raw_last_visit, date_format).date()
                break
            except ValueError:
                continue
        if parsed_date is None:
            raise ValueError(
                'last_visit_date must use YYYY-MM-DD or M/D/YYYY format'
            )
        data['imported_last_visit_date'] = parsed_date

    return data


def contacts_from_csv_row(row):
    """Return normalized contacts from legacy and numbered CSV columns."""
    numbered = {}
    for column, raw_value in row.items():
        match = NUMBERED_CONTACT_RE.match(column or '')
        if not match:
            continue
        index = int(match.group(1))
        field = match.group(2)
        numbered.setdefault(index, {})[field] = (raw_value or '').strip()

    legacy = {
        'name': (
            (row.get('primary_contact_name') or '').strip()
            or (row.get('contact_name') or '').strip()
        ),
        'title': (
            (row.get('primary_contact_title') or '').strip()
            or (row.get('contact_title') or '').strip()
        ),
        'email': (
            (row.get('primary_contact_email') or '').strip()
            or (row.get('contact_email') or '').strip()
        ),
        'phone': (
            (row.get('primary_contact_phone') or '').strip()
            or (row.get('contact_phone') or '').strip()
        ),
    }

    if numbered:
        if legacy['name']:
            numbered.setdefault(1, {})
            for field, value in legacy.items():
                if value and not numbered[1].get(field):
                    numbered[1][field] = value
        contacts = [numbered[index] for index in sorted(numbered)]
    else:
        contacts = [legacy] if any(legacy.values()) else []

    normalized = []
    for position, contact in enumerate(contacts):
        values = {field: (contact.get(field) or '').strip() for field in ('name', 'title', 'email', 'phone')}
        if not any(values.values()):
            continue
        if not values['name']:
            raise ValueError(f'contact_{position + 1}_name is required when contact details are provided')
        if values['email']:
            try:
                validate_email(values['email'])
            except ValidationError as exc:
                raise ValueError(f'invalid email for contact {position + 1}') from exc
        values['is_primary'] = not normalized
        normalized.append(values)
    return normalized


def replace_company_contacts(company, contacts):
    if not contacts:
        return
    company.contacts.all().delete()
    for contact in contacts:
        company.contacts.create(**contact)
    company.sync_primary_contact()
