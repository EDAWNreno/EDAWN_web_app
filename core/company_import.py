from datetime import datetime


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
