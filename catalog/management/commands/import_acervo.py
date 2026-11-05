import json
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.text import slugify

from catalog.models import Aula, AulaImagem, Conceito, Disciplina, Trilha
from catalog.parser import parse_lesson_markdown, split_frontmatter


class Command(BaseCommand):
    help = 'Importa aulas canônicas do acervo PROF-TONI.'

    COVER_NAMES = ('capa.png', 'capa.jpg', 'capa.jpeg', 'capa.webp')
    # Figuras do corpo da aula: pasta `img/` ao lado da canonica.md.
    BODY_IMAGE_DIRNAME = 'img'
    BODY_IMAGE_SUFFIXES = ('.png', '.jpg', '.jpeg', '.webp', '.gif')

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
        parser.add_argument(
            '--prune',
            action='store_true',
            help=(
                'Remove do catálogo as aulas que saíram do manifesto (ex.: '
                'renumeradas). Publicações migram para a aula sucessora '
                '(mesmo slug na mesma trilha); aula com progresso de aluno '
                'sem sucessora é mantida e listada.'
            ),
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Com --prune: só lista o que seria removido, sem importar nem alterar nada.',
        )

    def handle(self, *args, **options):
        root_path = Path(options['path']).expanduser().resolve()
        disciplina_filter = options.get('disciplina')
        force = options.get('force', False)
        prune = options.get('prune', False)
        dry_run = options.get('dry_run', False)

        if not root_path.exists():
            raise CommandError(f'Caminho não encontrado: {root_path}')
        if dry_run and not prune:
            raise CommandError('--dry-run só vale junto com --prune.')

        manifest = self.load_manifest(root_path)

        if dry_run:
            pruned = self.prune_orphans(manifest, disciplina_filter, apply=False)
            self.stdout.write(
                self.style.WARNING(
                    'Simulação (nada alterado): '
                    f'{pruned["removed"]} órfãs seriam removidas, '
                    f'{pruned["moved"]} publicações migradas, '
                    f'{pruned["dropped"]} publicações duplicadas descartadas, '
                    f'{pruned["kept"]} órfãs mantidas.'
                )
            )
            return

        self.import_disciplines(manifest)
        report = self.import_lessons(root_path, manifest, disciplina_filter, force)

        summary = (
            'Importação concluída: '
            f'{report["created"]} criadas, '
            f'{report["updated"]} atualizadas, '
            f'{report["skipped"]} ignoradas'
        )
        if prune:
            pruned = self.prune_orphans(manifest, disciplina_filter, apply=True)
            summary += (
                f'; {pruned["removed"]} órfãs removidas'
                + (f', {pruned["kept"]} mantidas (ver log)' if pruned['kept'] else '')
            )
        # A view "Importar do GitHub" mostra só a última linha: o resumo
        # precisa sair inteiro nela.
        self.stdout.write(self.style.SUCCESS(summary + '.'))

    def manifest_keys(self, manifest, disciplina_filter):
        keys = set()
        for raw_lesson in self.as_list(manifest.get('lessons')):
            disciplina_slug = self.get_value(raw_lesson, 'disciplina')
            if disciplina_filter and disciplina_slug != disciplina_filter:
                continue
            key = (
                disciplina_slug,
                self.get_value(raw_lesson, 'trilha'),
                self.to_int(self.get_value(raw_lesson, 'ordem')),
                self.get_value(raw_lesson, 'slug'),
            )
            if all(part not in (None, '') for part in key):
                keys.add(key)
        return keys

    def prune_orphans(self, manifest, disciplina_filter, apply):
        '''Remove aulas do catálogo cuja chave não está mais no manifesto.

        O import é idempotente por `(disciplina, trilha, ordem, slug)`: quando o
        acervo renumera uma aula, a antiga fica para trás e aparecem dois
        números iguais na trilha. Para cada publicação da órfã:
        - existe sucessora (mesmo slug na mesma trilha, chave no manifesto) e a
          turma ainda não a tem: a publicação migra para ela, com o progresso;
        - a turma já tem a sucessora e a publicação da órfã não tem progresso
          nem material: a publicação duplicada é descartada;
        - qualquer outro caso: a órfã é mantida e listada para decisão humana.
        '''
        from classroom.models import AulaPublicada
        from materials.models import Material

        keys = self.manifest_keys(manifest, disciplina_filter)
        if not keys:
            # Manifesto vazio ou corrompido no escopo apagaria o catálogo inteiro.
            raise CommandError('--prune recusado: o manifesto não tem aulas no escopo.')

        report = {'removed': 0, 'moved': 0, 'dropped': 0, 'kept': 0}
        candidates = Aula.objects.select_related('disciplina', 'trilha').order_by(
            'disciplina__slug', 'trilha__slug', 'ordem', 'slug'
        )
        if disciplina_filter:
            candidates = candidates.filter(disciplina__slug=disciplina_filter)

        for aula in candidates:
            key = (aula.disciplina.slug, aula.trilha.slug, aula.ordem, aula.slug)
            if key in keys:
                continue

            successors = [
                other
                for other in Aula.objects.filter(
                    disciplina=aula.disciplina, trilha=aula.trilha, slug=aula.slug
                ).exclude(pk=aula.pk)
                if (other.disciplina.slug, other.trilha.slug, other.ordem, other.slug) in keys
            ]
            successor = successors[0] if len(successors) == 1 else None

            plan = []
            blocked = []
            for pub in aula.publicacoes.select_related('turma'):
                has_data = (
                    pub.progressos.exists()
                    or Material.objects.filter(aula_publicada=pub).exists()
                )
                if successor is None:
                    if has_data:
                        blocked.append(f'{pub.turma} (progresso/material, sem sucessora)')
                    else:
                        plan.append(('drop', pub))
                elif not AulaPublicada.objects.filter(turma=pub.turma, aula=successor).exists():
                    plan.append(('move', pub))
                elif not has_data:
                    plan.append(('drop', pub))
                else:
                    blocked.append(f'{pub.turma} (já tem a sucessora e há progresso/material)')

            label = f'{aula.disciplina.slug}/{aula.trilha.slug}/{aula.ordem:02d}-{aula.slug}'
            if blocked:
                report['kept'] += 1
                self.stderr.write(f'Órfã mantida: {label} — {"; ".join(blocked)}')
                continue

            target = f' → {successor.ordem:02d}' if successor else ' (sem sucessora)'
            moves = sum(1 for action, _ in plan if action == 'move')
            drops = len(plan) - moves
            self.stdout.write(
                f'{"Removendo" if apply else "Removeria"} órfã {label}{target}: '
                f'{moves} publicações migradas, {drops} descartadas.'
            )
            report['removed'] += 1
            report['moved'] += moves
            report['dropped'] += drops
            if apply:
                self.delete_orphan(aula, successor, plan)

        return report

    @transaction.atomic
    def delete_orphan(self, aula, successor, plan):
        from notifications.models import Notificacao

        for action, pub in plan:
            if action == 'move':
                # Mesmo pk: o link das notificações já enviadas continua válido,
                # e o signal não reenvia (a publicação já estava publicada).
                pub.aula = successor
                pub.save(update_fields=['aula', 'updated_at'])
            else:
                # "Aula liberada" de uma publicação descartada levaria a um 404.
                Notificacao.objects.filter(
                    link=reverse('classroom:aluno_aula_detail', kwargs={'pk': pub.pk})
                ).delete()
                pub.delete()

        # Capa e figuras têm nome `{disciplina}-{slug}`, sem ordem: a órfã e a
        # sucessora costumam apontar para o MESMO arquivo. Só apaga arquivo que
        # nenhum outro registro usa.
        files = []
        if aula.imagem and not Aula.objects.filter(imagem=aula.imagem.name).exclude(pk=aula.pk).exists():
            files.append(aula.imagem)
        for imagem in aula.imagens.all():
            if imagem.arquivo and not AulaImagem.objects.filter(
                arquivo=imagem.arquivo.name
            ).exclude(pk=imagem.pk).exists():
                files.append(imagem.arquivo)

        aula.delete()
        for field_file in files:
            transaction.on_commit(lambda f=field_file: f.storage.delete(f.name))

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

    def load_concept_labels(self, manifest):
        '''Espelha `conceitos[]` do manifesto e devolve slug -> nome.

        Alimenta a resolução de `[[slug]]` nas aulas. Fica também no banco
        porque o roteiro do professor é renderizado em runtime, fora do import.
        Manifesto antigo, sem a chave `conceitos`, devolve vazio e o parser cai
        no fallback.
        '''
        labels = {}
        for raw in self.as_list(manifest.get('conceitos')):
            slug = self.get_value(raw, 'slug')
            nome = self.get_value(raw, 'nome', 'conceito', 'label')
            if slug and nome:
                labels[slug] = nome
                Conceito.objects.update_or_create(
                    slug=slug,
                    defaults={
                        'nome': nome,
                        'disciplina_slug': self.get_value(raw, 'disciplina') or '',
                    },
                )
        return labels

    def import_lessons(self, root_path, manifest, disciplina_filter, force):
        report = {'created': 0, 'updated': 0, 'skipped': 0}
        concept_labels = self.load_concept_labels(manifest)

        for raw_lesson in self.as_list(manifest.get('lessons')):
            disciplina_slug = self.get_value(raw_lesson, 'disciplina')
            if disciplina_filter and disciplina_slug != disciplina_filter:
                continue

            canonical_path = self.find_canonical_path(root_path, raw_lesson)
            if canonical_path is None:
                self.stderr.write(f'canonica.md não encontrada para {raw_lesson}')
                report['skipped'] += 1
                continue

            # Só o frontmatter aqui. A conversão markdown -> HTML acontece
            # dentro de upsert_lesson, depois que as imagens do corpo já estão
            # no banco (ver ORDEM CRÍTICA lá).
            try:
                content = canonical_path.read_text(encoding='utf-8')
                frontmatter, body = split_frontmatter(content)
            except Exception as exc:
                self.stderr.write(f'Erro ao ler {canonical_path}: {exc}')
                report['skipped'] += 1
                continue

            lesson_data = {**raw_lesson, **frontmatter}
            try:
                imported = self.upsert_lesson(
                    canonical_path,
                    lesson_data,
                    content,
                    body,
                    concept_labels,
                    force,
                )
            except Exception as exc:
                self.stderr.write(f'Erro ao processar {canonical_path}: {exc}')
                imported = 'skipped'
            report[imported] += 1

        return report

    @transaction.atomic
    def upsert_lesson(self, canonical_path, data, content, body, concept_labels, force=False):
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
        # O rótulo oficial da trilha vem de `disciplinas[].trilhas[]` do
        # manifesto (import_disciplines). Aqui só se cria a trilha que faltar,
        # com rótulo de reserva: sobrescrever a cada aula trocava
        # "JavaScript na Prática" por "Javascript Na Pratica".
        explicit_label = self.get_value(data, 'trilha_label', 'trilha_nome')
        if explicit_label:
            trilha = self.upsert_trilha(
                disciplina, {'slug': trilha_slug, 'label': explicit_label}
            )
        else:
            trilha, _ = Trilha.objects.get_or_create(
                disciplina=disciplina,
                slug=trilha_slug,
                defaults={'label': trilha_slug.replace('-', ' ').title()},
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
            # As figuras do corpo também são sincronizadas aqui: a pasta `img/`
            # pode ter aparecido sem bump de versão, e na primeira execução
            # depois desta feature toda aula já importada cairia neste caminho.
            # Se algo mudou, o HTML precisa ser refeito para apontar para os
            # arquivos novos.
            if self.sync_body_images(aula, canonical_path):
                aula.conteudo_html = parse_lesson_markdown(
                    content, concept_labels=concept_labels
                ).html
                aula.conteudo_md = body
                aula.save(update_fields=['conteudo_html', 'conteudo_md', 'updated_at'])
                return 'updated'
            return 'skipped'

        # `conteudo_html` fica de fora: é preenchido depois da ingestão das
        # imagens. Em atualização, o HTML antigo sobrevive até lá, então uma
        # falha de renderização (rollback da transação) não zera a aula.
        defaults = {
            'titulo': self.get_value(data, 'titulo', 'title') or slug.replace('-', ' ').title(),
            'tema': self.get_value(data, 'tema') or '',
            'objetivos': self.ensure_list(self.get_value(data, 'objetivos')),
            'prerequisitos': self.ensure_list(self.get_value(data, 'prerequisitos')),
            'modo_origem': self.get_value(data, 'modo_origem') or 'canonica_md',
            'conteudo_md': body,
            'status': self.get_value(data, 'status') or Aula.Status.APROVADA,
            'versao': versao,
            'atualizado_em': source_updated,
            'source_path': str(canonical_path),
        }

        if aula:
            outcome = 'updated'
            for field, value in defaults.items():
                setattr(aula, field, value)
        else:
            outcome = 'created'
            aula = Aula(
                disciplina=disciplina,
                trilha=trilha,
                ordem=ordem,
                slug=slug,
                **defaults,
            )

        self.apply_cover_image(aula, canonical_path, data)
        aula.save()

        # ORDEM CRÍTICA: as figuras do corpo precisam estar no banco ANTES da
        # conversão markdown -> HTML. O parser resolve `![alt](img/arquivo.png)`
        # consultando `aula.imagens`, então renderizar antes produziria links
        # quebrados. Não inverta estas duas linhas.
        self.sync_body_images(aula, canonical_path)
        aula.conteudo_html = parse_lesson_markdown(
            content, concept_labels=concept_labels
        ).html
        aula.save(update_fields=['conteudo_html', 'updated_at'])
        return outcome

    def find_body_image_sources(self, canonical_path):
        '''Mapeia `nome do arquivo -> Path` da pasta `img/` da aula.'''
        source_dir = canonical_path.parent / self.BODY_IMAGE_DIRNAME
        if not source_dir.is_dir():
            return {}
        # O nome é o caminho relativo a `img/`, exatamente como o markdown
        # escreve em `![alt](img/...)` — inclusive com subpasta.
        return {
            entry.relative_to(source_dir).as_posix(): entry
            for entry in sorted(source_dir.rglob('*'))
            if entry.is_file() and entry.suffix.lower() in self.BODY_IMAGE_SUFFIXES
        }

    def sync_body_images(self, aula, canonical_path):
        '''Sincroniza `img/` com `AulaImagem`. Devolve True se algo mudou.

        Idempotente pelo mesmo critério da capa: arquivo já presente com o mesmo
        tamanho não é re-salvo. Registro sem arquivo correspondente na origem é
        removido, junto com o arquivo em media.
        '''
        sources = self.find_body_image_sources(canonical_path)
        existing = {imagem.nome: imagem for imagem in aula.imagens.all()}
        changed = False

        for nome, source in sources.items():
            imagem = existing.get(nome)
            if imagem is None:
                imagem = AulaImagem(aula=aula, nome=nome)
            elif imagem.arquivo:
                try:
                    if imagem.arquivo.size == source.stat().st_size:
                        continue
                except (OSError, ValueError):
                    pass
                # Conteúdo trocou: descarta o arquivo antigo para o media não
                # acumular versões órfãs a cada reimport.
                imagem.arquivo.delete(save=False)

            target = self.body_image_target_name(aula, nome)
            # O nome de destino é determinístico. Um arquivo remanescente em
            # media (banco recriado, import anterior) faria o storage inventar
            # um sufixo aleatório e a URL deixaria de ser previsível.
            storage = imagem.arquivo.storage
            stored_name = imagem.arquivo.field.generate_filename(imagem, target)
            if storage.exists(stored_name):
                storage.delete(stored_name)

            imagem.arquivo.save(target, ContentFile(source.read_bytes()), save=False)
            imagem.save()
            changed = True

        for nome, imagem in existing.items():
            if nome in sources:
                continue
            imagem.arquivo.delete(save=False)
            imagem.delete()
            changed = True

        return changed

    def body_image_target_name(self, aula, nome):
        flat = nome.lower().replace('/', '-')
        return f'{aula.disciplina.slug}-{aula.slug}-{flat}'

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
            # Capa trocou: descarta o arquivo antigo para o media não acumular
            # versões órfãs a cada reimport.
            aula.imagem.delete(save=False)

        target_name = f'{aula.disciplina.slug}-{aula.slug}{source.suffix.lower()}'
        # O nome de destino é determinístico. Um arquivo remanescente em media
        # (banco recriado, import anterior) faria o storage inventar um sufixo
        # aleatório, e a capa antiga ficaria para sempre sem dono.
        storage = aula.imagem.storage
        stored_name = aula.imagem.field.generate_filename(aula, target_name)
        if storage.exists(stored_name):
            storage.delete(stored_name)

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
