from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from catalog.models import Disciplina
from classroom.models import Turma


class Command(BaseCommand):
    help = 'Garante a turma de Inteligência Artificial em produção.'

    def add_arguments(self, parser):
        parser.add_argument('--professor-email', default='elvertoni@gmail.com')
        parser.add_argument('--nome', default='Inteligência Artificial')
        parser.add_argument('--serie', default='Extra')
        parser.add_argument('--ano-letivo', type=int, default=2026)
        parser.add_argument('--codigo-convite', default='IA2026')

    @transaction.atomic
    def handle(self, *args, **options):
        professor = self.get_professor(options['professor_email'])
        disciplina, _ = Disciplina.objects.update_or_create(
            slug='inteligencia-artificial',
            defaults={
                'label': 'Inteligência Artificial',
                'serie': options['serie'],
                'status': 'aprovada',
            },
        )

        turma, created = Turma.objects.get_or_create(
            nome=options['nome'],
            ano_letivo=options['ano_letivo'],
            professor=professor,
            defaults={
                'disciplina': disciplina,
                'serie': options['serie'],
                'codigo_convite': self.unique_invite_code(options['codigo_convite']),
                'ativa': True,
            },
        )
        if not created:
            turma.disciplina = disciplina
            turma.serie = options['serie']
            turma.ativa = True
            if not turma.codigo_convite:
                turma.codigo_convite = self.unique_invite_code(options['codigo_convite'])
            turma.save(update_fields=['disciplina', 'serie', 'ativa', 'codigo_convite', 'updated_at'])

        status = 'criada' if created else 'atualizada'
        self.stdout.write(
            self.style.SUCCESS(
                f'Turma {status}: {turma.nome} '
                f'({turma.ano_letivo}) · convite {turma.codigo_convite}'
            )
        )

    def get_professor(self, email):
        professor = (
            User.objects.filter(email=email).first()
            or User.objects.filter(role=User.Role.PROFESSOR).order_by('id').first()
            or User.objects.filter(role=User.Role.ADMIN).order_by('id').first()
            or User.objects.filter(is_superuser=True).order_by('id').first()
        )
        if professor is None:
            raise CommandError(
                'Nenhum professor/admin/superuser encontrado para vincular a turma.'
            )
        return professor

    def unique_invite_code(self, base_code):
        code = base_code
        suffix = 1
        while Turma.objects.filter(codigo_convite=code).exists():
            code = f'{base_code}{suffix}'
            suffix += 1
        return code
