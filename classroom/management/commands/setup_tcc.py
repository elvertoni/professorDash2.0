# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from catalog.models import Disciplina, Aula
from classroom.models import Turma, Matricula, AulaPublicada
from accounts.models import User

class Command(BaseCommand):
    help = 'Cria a(s) turma(s) de TCC de 3º ano, matricula os mesmos alunos e publica as aulas correspondentes.'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando o setup da turma de TCC...')

        # 1. Localizar a disciplina de TCC
        try:
            disciplina_tcc = Disciplina.objects.get(slug='tcc')
            self.stdout.write(self.style.SUCCESS(f"Disciplina TCC encontrada: '{disciplina_tcc.label}'"))
        except Disciplina.DoesNotExist:
            self.stdout.write(self.style.ERROR("Disciplina TCC com slug='tcc' não encontrada! Por favor, execute o comando 'import_acervo' primeiro."))
            return

        # 2. Localizar turmas ativas de 3º ano
        # Buscamos turmas cuja série contenha '3' e estejam ativas no ano letivo corrente (2026)
        turmas_3ano = Turma.objects.filter(serie__icontains='3', ativa=True).exclude(disciplina=disciplina_tcc)
        if not turmas_3ano.exists():
            self.stdout.write(self.style.WARNING("Nenhuma turma de 3º ano ativa encontrada."))
            return

        # 3. Processar cada turma de 3º ano para criar a turma de TCC e matricular alunos
        for turma_orig in turmas_3ano:
            self.stdout.write(f"\nProcessando turma: '{turma_orig.nome}' (Série: '{turma_orig.serie}', Ano Letivo: {turma_orig.ano_letivo})")

            # Nome da turma de TCC correspondente
            nome_turma_tcc = f"TCC · {turma_orig.nome}"

            with transaction.atomic():
                # Obter ou criar a turma de TCC correspondente
                turma_tcc, created = Turma.objects.get_or_create(
                    nome=nome_turma_tcc,
                    disciplina=disciplina_tcc,
                    serie=turma_orig.serie,
                    ano_letivo=turma_orig.ano_letivo,
                    professor=turma_orig.professor,
                    defaults={'ativa': True}
                )

                if created:
                    self.stdout.write(self.style.SUCCESS(f"Turma criada: '{turma_tcc.nome}' (Código: {turma_tcc.codigo_convite})"))
                else:
                    self.stdout.write(f"Turma já existente: '{turma_tcc.nome}'")

                # Matricular todos os alunos ativos da turma original
                matriculas_orig = Matricula.objects.filter(turma=turma_orig, status=Matricula.Status.ATIVA)
                novas_matriculas = 0
                for mat_orig in matriculas_orig:
                    _, mat_created = Matricula.objects.get_or_create(
                        turma=turma_tcc,
                        aluno=mat_orig.aluno,
                        defaults={
                            'status': Matricula.Status.ATIVA,
                            'data_matricula': mat_orig.data_matricula
                        }
                    )
                    if mat_created:
                        novas_matriculas += 1

                self.stdout.write(f"Alunos matriculados: {novas_matriculas} novos alunos (total de matriculados na turma: {turma_tcc.matriculas.count()})")

                # Publicar todas as aulas aprovadas da disciplina TCC
                aulas_tcc = Aula.objects.filter(disciplina=disciplina_tcc, status=Aula.Status.APROVADA)
                novas_aulas_publicadas = 0
                now = timezone.now()
                for aula in aulas_tcc:
                    _, pub_created = AulaPublicada.objects.get_or_create(
                        turma=turma_tcc,
                        aula=aula,
                        defaults={
                            'disponivel_em': now,
                            'ordem_na_turma': aula.ordem,
                            'publicada': True,
                        }
                    )
                    if pub_created:
                        novas_aulas_publicadas += 1

                self.stdout.write(f"Aulas publicadas: {novas_aulas_publicadas} novas aulas (total de publicadas na turma: {turma_tcc.aulas_publicadas.count()})")

        self.stdout.write(self.style.SUCCESS('\nSetup da disciplina de TCC concluído com sucesso!'))
