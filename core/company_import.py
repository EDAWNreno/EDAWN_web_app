import csv
from dataclasses import dataclass, field
from datetime import datetime
import io
import re

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.html import format_html, format_html_join


NUMBERED_CONTACT_RE = re.compile(r'^contact_(\d+)_(name|title|email|phone)$')

MAX_LISTED_ROW_ERRORS = 25


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

OTHER_RECOGNIZED_COLUMNS = {
    'last_visit_date', 'last_visit',
    'contact_email', 'primary_contact_email',
    'contact_phone', 'primary_contact_phone',
}

# Common spreadsheet headers, keyed by lowercase letters/digits only, mapped
# to the portal column the importer actually reads.
HEADER_SUGGESTIONS = {
    'company': 'name',
    'companyname': 'name',
    'businessname': 'name',
    'organization': 'name',
    'organizationname': 'name',
    'accountname': 'name',
    'streetaddress': 'address',
    'street': 'address',
    'address1': 'address',
    'zipcode': 'zip_code',
    'postalcode': 'zip_code',
    'phonenumber': 'phone',
    'companyphone': 'phone',
    'emailaddress': 'email',
    'url': 'website',
    'primarycontact': 'contact_1_name, with phone and email split into contact_1_phone and contact_1_email',
    'contact': 'contact_1_name',
    'contactperson': 'contact_1_name',
    'mostrecentvisitdate': 'last_visit_date',
    'lastvisitdate': 'last_visit_date',
    'lastvisited': 'last_visit_date',
    'visitdate': 'last_visit_date',
}


def _is_recognized_column(column):
    return (
        column in CSV_FIELD_MAP
        or column in OTHER_RECOGNIZED_COLUMNS
        or bool(NUMBERED_CONTACT_RE.match(column))
    )


def _suggest_column(column):
    if column.strip().lower() != column and _is_recognized_column(column.strip().lower()):
        return column.strip().lower()
    return HEADER_SUGGESTIONS.get(re.sub(r'[^a-z0-9]', '', column.lower()))


def _describe_column(column):
    suggestion = _suggest_column(column)
    if suggestion:
        return f'"{column}" (rename to {suggestion})'
    return f'"{column}"'


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
                f'last visit date "{raw_last_visit}" is not a valid date '
                '(use YYYY-MM-DD or M/D/YYYY)'
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
            raise ValueError(
                f'contact {position + 1} has a title, email, or phone but no name '
                f'(fill in contact_{position + 1}_name, or move a general phone '
                'number to the company phone column)'
            )
        if values['email']:
            try:
                validate_email(values['email'])
            except ValidationError as exc:
                raise ValueError(
                    f'contact {position + 1} email "{values["email"]}" is not a valid email address'
                ) from exc
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


class CSVImportError(Exception):
    """The file cannot be imported at all; nothing was changed."""


@dataclass
class CompanyImportResult:
    created: int = 0
    updated: int = 0
    restored: int = 0
    unchanged_existing: int = 0
    row_errors: list = field(default_factory=list)
    ignored_columns: list = field(default_factory=list)

    @property
    def skipped(self):
        return self.unchanged_existing + len(self.row_errors)

    @property
    def imported(self):
        return self.created + self.updated + self.restored


def decode_csv_upload(uploaded_file):
    try:
        return uploaded_file.read().decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise CSVImportError(
            'This file could not be read as a UTF-8 CSV. In Excel, use '
            'File → Save As → "CSV UTF-8 (Comma delimited)" and upload it again.'
        ) from exc


def import_companies_from_csv(decoded, overwrite):
    from .models import Company

    reader = csv.DictReader(io.StringIO(decoded))
    columns = [(column or '').strip() for column in (reader.fieldnames or [])]
    if not any(columns):
        raise CSVImportError('This file is empty. The first row must contain column headers.')
    if 'name' not in reader.fieldnames:
        found = ', '.join(_describe_column(column) for column in columns if column)
        raise CSVImportError(
            'No companies were imported because this file has no "name" column, '
            'which holds the company name. Column names must match the CSV Format '
            f'guide exactly. Columns found: {found}.'
        )

    result = CompanyImportResult(
        ignored_columns=[column for column in columns if column and not _is_recognized_column(column)],
    )
    for i, row in enumerate(reader, start=2):
        name = (row.get('name') or '').strip()
        if not name:
            if any((value or '').strip() for value in row.values() if isinstance(value, str)):
                result.row_errors.append(f'Row {i}: company name is blank')
            continue
        try:
            data = company_data_from_csv_row(row)
            contact_data = contacts_from_csv_row(row)
        except ValueError as exc:
            result.row_errors.append(f'Row {i} ({name}): {exc}')
            continue

        existing = Company.objects.filter(name__iexact=name).first()
        if existing:
            if existing.is_archived:
                if overwrite:
                    for model_field, val in data.items():
                        setattr(existing, model_field, val)
                existing.is_archived = False
                existing.archived_at = None
                existing.archived_by = None
                existing.save()
                if overwrite:
                    replace_company_contacts(existing, contact_data)
                result.restored += 1
                continue
            if overwrite:
                for model_field, val in data.items():
                    setattr(existing, model_field, val)
                existing.save()
                replace_company_contacts(existing, contact_data)
                result.updated += 1
            else:
                result.unchanged_existing += 1
        else:
            data['name'] = name
            company = Company.objects.create(**data)
            replace_company_contacts(company, contact_data)
            result.created += 1

    if not result.imported and not result.skipped:
        raise CSVImportError('This file has column headers but no company rows.')
    return result


def report_company_import(request, result):
    summary = (
        f'Import complete: {result.created} created, {result.updated} updated, '
        f'{result.restored} restored, {result.skipped} skipped.'
    )
    if result.row_errors and not result.imported:
        messages.error(request, summary)
    elif result.row_errors or result.ignored_columns:
        messages.warning(request, summary)
    else:
        messages.success(request, summary)

    if result.unchanged_existing:
        messages.info(
            request,
            f'{result.unchanged_existing} compan'
            f'{"y was" if result.unchanged_existing == 1 else "ies were"} already in the '
            'portal and left unchanged. Check "Overwrite existing" to update them.',
        )

    if result.row_errors:
        listed = result.row_errors[:MAX_LISTED_ROW_ERRORS]
        remaining = len(result.row_errors) - len(listed)
        messages.warning(request, format_html(
            '{} row{} skipped because of problems. Fix these rows and upload the file again:'
            '<ul class="mb-0 mt-1">{}</ul>{}',
            len(result.row_errors),
            '' if len(result.row_errors) == 1 else 's',
            format_html_join('', '<li>{}</li>', ((error,) for error in listed)),
            f'…and {remaining} more.' if remaining else '',
        ))

    if result.ignored_columns:
        messages.warning(
            request,
            'These columns were not recognized and were ignored: '
            + ', '.join(_describe_column(column) for column in result.ignored_columns)
            + '.',
        )
