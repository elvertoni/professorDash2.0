import json
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.text import slugify

from catalog.models import Aula, Disciplina, Trilha
from catalog.parser import parse_lesson_markdown


class Command(BaseCommand):
    help = 'Importa aulas canônicas do acervo PROF-TONI.'

    COVER_NAMES = ('capa.png', 'capa.jpg', 'capa.jpeg', 'capa.webp')

    def add_arguments(self, parser):
        parser.add_argument('--path', required=True, help='Caminho para o repositório PROF-TONI.')
        parser.add_argument(
            '--only-aprovada',
            action='store_true',
            help=(
                'Mantido por compatibilidade: o import da fase atual sempre '
                'importa apenas aprovadas.'
            ),
        )
        parser.add_argument('--disciplina', help='Slug da disciplina a importar.')
        parser.add_argument(
            '--force',
            action='store_true',
            help=(
                'Reprocessa e atualiza aulas existentes mesmo quando versao e '
                'atualizado_em nao mudaram.'
            ),
        )

    def handle(self, *args, **options):
        root_path = Path(options['path']).expanduser().resolve()
        disciplina_filter = options.get('disciplina')
        force = options.get('force', False)

        if not root_path.exists():
            raise CommandError(f'Caminho não encontrado: {root_path}')

        manifest = self.load_manifest(root_path)
        self.import_disciplines(manifest)
        report = self.import_lessons(root_path, manifest, disciplina_filter, force)

        self.stdout.write(
            self.style.SUCCESS(
                'Importação concluída: '
                f'{report["created"]} criadas, '
                f'{report["updated"]} atualizadas, '
                f'{report["skipped"]} ignoradas.'
            )
        )

    def load_manifest(self, root_path):
        manifest_path = root_path / 'manifesto.json'
        if not manifest_path.exists():
            raise CommandError(f'manifesto.json não encontrado em {root_path}')

        with manifest_path.open(encoding='utf-8') as manifest_file:
            return json.load(manifest_file)

    def import_disciplines(self, manifest):
        for raw_disciplina in self.as_list(manifest.get('disciplinas')):
            slug = self.get_value(raw_disciplina, 'slug', 'id')
            if not slug:
                continue

            disciplina, _ = Disciplina.objects.update_or_create(
                slug=slug,
                defaults={
                    'label': self.get_value(raw_disciplina, 'label', 'nome', 'titulo') or slug,
                    'serie': self.get_value(raw_disciplina, 'serie') or '',
                    'status': self.get_value(raw_disciplina, 'status') or '',
                },
            )

            if isinstance(raw_disciplina, dict):
                for raw_trilha in self.as_list(raw_disciplina.get('trilhas')):
                    self.upsert_trilha(disciplina, raw_trilha)

    def import_lessons(self, root_path, manifest, disciplina_filter, force):
        report = {'created': 0, 'updated': 0, 'skipped': 0}

        for raw_lesson in self.as_list(manifest.get('lessons')):
            disciplina_slug = self.get_value(raw_lesson, 'disciplina')
            if disciplina_filter and disciplina_slug != disciplina_filter:
                continue

            canonical_path = self.find_canonical_path(root_path, raw_lesson)
            if canonical_path is None:
                self.stderr.write(f'canonica.md não encontrada para {raw_lesson}')
                report['skipped'] += 1
                continue

            try:
                parsed = parse_lesson_markdown(canonical_path.read_text(encoding='utf-8'))
            except Exception as exc:
                self.stderr.write(f'Erro ao processar {canonical_path}: {exc}')
                report['skipped'] += 1
                continue
            lesson_data = {**raw_lesson, **parsed.frontmatter}
            imported = self.upsert_lesson(
                canonical_path,
                lesson_data,
                parsed.body,
                parsed.html,
                force,
            )
            report[imported] += 1

        return report

    def upsert_lesson(self, canonical_path, data, body, html_content, force=False):
        disciplina_slug = self.get_value(data, 'disciplina')
        trilha_slug = self.get_value(data, 'trilha')
        slug = self.get_value(data, 'slug') or slugify(self.get_value(data, 'titulo') or '')
        ordem = self.to_int(self.get_value(data, 'ordem'))

        if not all([disciplina_slug, trilha_slug, slug, ordem is not None]):
            self.stderr.write(f'Metadados insuficientes em {canonical_path}')
            return 'skipped'

        disciplina, _ = Disciplina.objects.get_or_create(
            slug=disciplina_slug,
            defaults={
                'label': disciplina_slug.replace('-', ' ').title(),
                'serie': self.get_value(data, 'serie') or '',
                'status': self.get_value(data, 'status') or '',
            },
        )
        trilha = self.upsert_trilha(
            disciplina,
            {
                'slug': trilha_slug,
                'label': (
                    self.get_value(data, 'trilha_label', 'trilha_nome')
                    or trilha_slug.replace('-', ' ').title()
                ),
            },
        )

        versao = str(self.get_value(data, 'versao') or '')
        source_updated = self.parse_source_datetime(self.get_value(data, 'atualizado_em'))

        aula = Aula.objects.filter(
            disciplina=disciplina,
            trilha=trilha,
            ordem=ordem,
            slug=slug,
        ).first()

        if (
            aula
            and not force
            and aula.versao == versao
            and aula.atualizado_em == source_updated
            and aula.status == (self.get_value(data, 'status') or Aula.Status.APROVADA)
            and aula.conteudo_html
        ):
            # Conteúdo inalterado: ainda assim faz backfill da capa se faltar.
            if self.apply_cover_image(aula, canonical_path, data):
                aula.save(update_fields=['imagem', 'updated_at'])
            return 'skipped'

        defaults = {
            'titulo': self.get_value(data, 'titulo', 'title') or slug.replace('-', ' ').title(),
            'tema': self.get_value(data, 'tema') or '',
            'objetivos': self.ensure_list(self.get_value(data, 'objetivos')),
            'prerequisitos': self.ensure_list(self.get_value(data, 'prerequisitos')),
            'modo_origem': self.get_value(data, 'modo_origem') or 'canonica_md',
            'conteudo_html': html_content,
            'conteudo_md': body,
            'status': self.get_value(data, 'status') or Aula.Status.APROVADA,
            'versao': versao,
            'atualizado_em': source_updated,
            'source_path': str(canonical_path),
        }

        if aula:
            for field, value in defaults.items():
                setattr(aula, field, value)
            self.apply_cover_image(aula, canonical_path, data)
            aula.save()
            return 'updated'

        aula = Aula(
            disciplina=disciplina,
            trilha=trilha,
            ordem=ordem,
            slug=slug,
            **defaults,
        )
        self.apply_cover_image(aula, canonical_path, data)
        aula.save()
        return 'created'

    def find_cover_path(self, canonical_path, data):
        lesson_dir = canonical_path.parent
        declared = self.get_value(data, 'imagem', 'capa', 'cover')
        if declared:
            candidate = (lesson_dir / declared).resolve()
            try:
                candidate.relative_to(lesson_dir.resolve())
            except ValueError:
                return None
            if candidate.is_file():
                return candidate
        for name in self.COVER_NAMES:
            candidate = lesson_dir / name
            if candidate.is_file():
                return candidate
        return None

    def apply_cover_image(self, aula, canonical_path, data):
        source = self.find_cover_path(canonical_path, data)
        if source is None:
            return False
        # Idempotente: mesma capa (mesmo tamanho) já presente => não re-salva.
        if aula.imagem:
            try:
                if aula.imagem.size == source.stat().st_size:
                    return False
            except (OSError, ValueError):
                pass
        target_name = f'{aula.disciplina.slug}-{aula.slug}{source.suffix.lower()}'
        aula.imagem.save(target_name, ContentFile(source.read_bytes()), save=False)
        return True

    def upsert_trilha(self, disciplina, raw_trilha):
        slug = self.get_value(raw_trilha, 'slug', 'id')
        if not slug:
            slug = slugify(self.get_value(raw_trilha, 'label', 'nome', 'titulo') or 'trilha')

        trilha, _ = Trilha.objects.update_or_create(
            disciplina=disciplina,
            slug=slug,
            defaults={
                'label': self.get_value(raw_trilha, 'label', 'nome', 'titulo') or slug,
            },
        )
        return trilha

    def find_canonical_path(self, root_path, raw_lesson):
        explicit_path = self.get_value(raw_lesson, 'source_path', 'path', 'canonical_path')
        if explicit_path:
            path = root_path / explicit_path
            if path.exists():
                return path

        disciplina = self.get_value(raw_lesson, 'disciplina')
        trilha = self.get_value(raw_lesson, 'trilha')
        ordem = self.to_int(self.get_value(raw_lesson, 'ordem'))
        slug = self.get_value(raw_lesson, 'slug')

        if disciplina and trilha and ordem is not None and slug:
            lesson_dir = root_path / 'aulas' / disciplina / trilha / f'{ordem:02d}-{slug}'
            path = lesson_dir / 'canonica.md'
            if path.exists():
                return path

        if slug:
            matches = list((root_path / 'aulas').glob(f'**/*{slug}/canonica.md'))
            if matches:
                return matches[0]

        return None

    def parse_source_datetime(self, value):
        if value is None:
            return None

        if hasattr(value, 'hour'):
            parsed = value
        else:
            parsed = parse_datetime(str(value))
            if parsed is None:
                parsed_date = parse_date(str(value))
                if parsed_date is None:
                    return None
                parsed = timezone.datetime.combine(parsed_date, timezone.datetime.min.time())

        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed

    def get_value(self, data, *keys):
        if not isinstance(data, dict):
            return None

        for key in keys:
            if key in data and data[key] not in (None, ''):
                return data[key]
        return None

    def as_list(self, value):
        if value is None:
            return []
        if isinstance(value, dict):
            return list(value.values())
        if isinstance(value, list):
            return value
        return []

    def ensure_list(self, value):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    def to_int(self, value):
        if value in (None, ''):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
