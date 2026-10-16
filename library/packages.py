import hashlib
import json
import re
from pathlib import Path, PurePosixPath

import yaml
from django.db import transaction

from .content import COLLECTIONS, normalize, plain_text
from .models import Note, Source

SOURCES = {
    'prof-toni': ('PROF-TONI', 'conceitos'),
    'pessoal': ('Cérebro pessoal', '3-recursos'),
}
SAMPLES = {
    'prof-toni': {
        'conceitos/inteligencia-artificial/rag.md',
        'conceitos/inovacao-inteligencia-artificial-e-robotica-educacional/aprendizagem-baseada-em-problemas.md',
        'conceitos/desenvolvimento-full-stack-e-cloud-computing/api-rest.md',
    },
    'pessoal': {
        '3-recursos/negocios/precificacao-de-projeto-de-ia.md',
        '3-recursos/agentes/central-de-operacoes-do-agente.md',
    },
}
MAX_PACKAGE_BYTES = 20 * 1024 * 1024
MAX_NOTE_BYTES = 250_000
FIELDS = {
    'path',
    'slug',
    'title',
    'aliases',
    'topic',
    'status',
    'collections',
    'body',
    'references',
    'source_updated',
}


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def validate_package(package):
    if not isinstance(package, dict) or set(package) != {'version', 'source', 'notes'}:
        raise ValueError('Estrutura de pacote inválida.')
    if (
        package['version'] != 1
        or not isinstance(package['source'], str)
        or package['source'] not in SOURCES
    ):
        raise ValueError('Versão ou acervo desconhecido.')
    notes = package['notes']
    if not isinstance(notes, list) or not notes or len(notes) > 5000:
        raise ValueError('O pacote deve conter entre 1 e 5000 notas.')
    paths = set()
    for data in notes:
        if not isinstance(data, dict) or set(data) != FIELDS:
            raise ValueError('Campos da nota inválidos.')
        for key, length in [
            ('path', 500),
            ('slug', 180),
            ('title', 300),
            ('topic', 180),
            ('status', 40),
            ('body', MAX_NOTE_BYTES),
            ('source_updated', 80),
        ]:
            value = data[key]
            if not isinstance(value, str) or len(value) > length or '\x00' in value:
                raise ValueError(f'Campo inválido: {key}.')
        path = PurePosixPath(data['path'])
        prefix = SOURCES[package['source']][1]
        if (
            path.is_absolute()
            or '..' in path.parts
            or '\\' in data['path']
            or len(path.parts) < 3
            or path.parts[0] != prefix
            or path.suffix != '.md'
            or str(path) != data['path']
        ):
            raise ValueError('Caminho fora das notas permitidas.')
        if data['path'] in paths:
            raise ValueError('Caminho repetido no pacote.')
        paths.add(data['path'])
        if not data['title'].strip() or not data['slug'].strip():
            raise ValueError('Título e slug são obrigatórios.')
        for key in ('aliases', 'references', 'collections'):
            if (
                not isinstance(data[key], list)
                or len(data[key]) > 200
                or any(
                    not isinstance(item, str) or len(item) > 2000 or '\x00' in item
                    for item in data[key]
                )
            ):
                raise ValueError(f'Lista inválida: {key}.')
        if not set(data['collections']).issubset(COLLECTIONS):
            raise ValueError('Coleção desconhecida.')
    return package


def build_package(root, source, selection='pilot'):
    root = Path(root).resolve(strict=True)
    _, prefix = SOURCES[source]
    folder = root / prefix
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError('Pasta de notas ausente ou simbólica.')
    notes = []
    for path in sorted(folder.rglob('*.md')):
        if path.is_symlink() or any(
            parent.is_symlink() for parent in path.parents if parent != root
        ):
            raise ValueError('Links simbólicos não são aceitos.')
        if not path.resolve().is_relative_to(root):
            raise ValueError('Nota fora do vault.')
        relative = path.relative_to(root).as_posix()
        if path.stat().st_size > MAX_NOTE_BYTES:
            raise ValueError(f'Nota muito grande: {relative}.')
        raw = path.read_text(encoding='utf-8-sig')
        match = re.match(r'\A---\s*\n(.*?)\n---\s*\n', raw, re.S)
        if not match:
            continue
        metadata = yaml.safe_load(match.group(1))
        if not isinstance(metadata, dict):
            raise ValueError(f'Metadados inválidos: {relative}.')
        status = str(metadata.get('status', 'rascunho'))
        if selection == 'pilot' and not (
            relative in SAMPLES[source] or (source == 'prof-toni' and status == 'vivo')
        ):
            continue
        collections = (
            ['estudar', 'preparar-aulas'] if source == 'prof-toni' else ['projetos']
        )
        notes.append(
            {
                'path': relative,
                'slug': str(metadata.get('slug', path.stem)),
                'title': str(
                    metadata.get('conceito') or metadata.get('titulo') or path.stem
                ),
                'aliases': metadata.get('aka', []) or [],
                'topic': str(
                    metadata.get('disciplina')
                    or metadata.get('tema')
                    or path.parent.name
                ),
                'status': status,
                'collections': collections,
                'body': raw[match.end() :].strip(),
                'references': metadata.get('fontes', []) or [],
                'source_updated': str(metadata.get('atualizado_em', '')),
            }
        )
    return validate_package({'version': 1, 'source': source, 'notes': notes})


def read_package(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_PACKAGE_BYTES + 1)
    if len(raw) > MAX_PACKAGE_BYTES:
        raise ValueError('Pacote excede 20 MiB.')
    return validate_package(json.loads(raw))


def import_package(package, owner, apply=False):
    validate_package(package)
    counts = {'created': 0, 'updated': 0, 'unchanged': 0}
    with transaction.atomic():
        # Serialize imports, including creation of the first Source row.
        type(owner).objects.select_for_update().get(pk=owner.pk)
        source = Source.objects.filter(key=package['source']).first()
        if source and source.owner_id != owner.pk:
            raise ValueError(
                'Acervo pertence a outra conta; transferência não é automática.'
            )
        if source is None and apply:
            source = Source.objects.create(
                key=package['source'], label=SOURCES[package['source']][0], owner=owner
            )
        existing = {n.path: n for n in source.notes.all()} if source else {}
        for data in package['notes']:
            note = existing.get(data['path'])
            checksum = digest(data)
            if note and note.digest == checksum:
                counts['unchanged'] += 1
                continue
            counts['updated' if note else 'created'] += 1
            values = dict(
                data,
                digest=checksum,
                search_title=normalize(data['title']),
                search_text=normalize(
                    ' '.join(
                        [
                            data['title'],
                            *data['aliases'],
                            plain_text(data['body']),
                        ]
                    )
                ),
            )
            instance = note or Note(source=source)
            for key, value in values.items():
                setattr(instance, key, value)
            instance.full_clean(
                exclude=['source'], validate_unique=False, validate_constraints=False
            )
            if apply:
                instance.save()
        if apply:
            source.revision = digest(package)
            source.save(update_fields=['revision', 'updated_at'])
    return counts
