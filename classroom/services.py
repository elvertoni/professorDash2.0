import csv
import unicodedata
from io import StringIO

from django.db import transaction
from django.utils.dateparse import parse_date

from .forms import StudentEnrollmentForm


HEADER_ALIASES = {
    'nome_completo': {'nome_completo', 'nome_completo', 'nome', 'aluno'},
    'email': {'email', 'e_mail', 'mail'},
    'school_registration': {
        'matricula_escolar',
        'matricula',
        'ra',
    },
    'grade': {'serie', 'grade'},
    'responsible_name': {'responsavel', 'responsible_name'},
    'birth_date': {'data_nascimento', 'nascimento'},
}


def import_students_from_csv(turma, uploaded_file):
    content = uploaded_file.read().decode('utf-8-sig')
    reader = csv.DictReader(StringIO(content))
    report = {
        'created': 0,
        'updated': 0,
        'errors': [],
    }

    if not reader.fieldnames:
        report['errors'].append('Arquivo sem cabeçalho.')
        return report

    for row_number, row in enumerate(reader, start=2):
        data = normalize_row(row)
        data['status'] = 'ativa'

        if not data.get('nome_completo') or not data.get('email'):
            report['errors'].append(
                f'Linha {row_number}: nome_completo e email são obrigatórios.'
            )
            continue

        form = StudentEnrollmentForm(data=data, turma=turma)
        if form.is_valid():
            with transaction.atomic():
                _, created = form.save()
            if created:
                report['created'] += 1
            else:
                report['updated'] += 1
        else:
            errors = '; '.join(
                f'{field}: {", ".join(messages)}'
                for field, messages in form.errors.items()
            )
            report['errors'].append(f'Linha {row_number}: {errors}')

    return report


def normalize_row(row):
    normalized = {}
    for target, aliases in HEADER_ALIASES.items():
        value = get_value(row, aliases)
        if target == 'birth_date' and value:
            value = normalize_date(value)
        normalized[target] = value
    return normalized


def get_value(row, aliases):
    for header, value in row.items():
        if normalize_header(header) in aliases:
            return (value or '').strip()
    return ''


def normalize_header(header):
    header = (header or '').strip().lower().replace('-', '_')
    header = unicodedata.normalize('NFKD', header).encode('ascii', 'ignore').decode()
    return header.replace(' ', '_')


def normalize_date(value):
    parsed = parse_date(value)
    if parsed:
        return parsed.isoformat()

    parts = value.split('/')
    if len(parts) == 3:
        day, month, year = parts
        return f'{year.zfill(4)}-{month.zfill(2)}-{day.zfill(2)}'

    return value
