from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import AlunoProfile, ProfessorProfile, User
from activities.models import Atividade, Entrega
from catalog.models import Aula, Disciplina, Trilha
from classroom.models import AulaPublicada, Matricula, ProgressoAula, Turma
from materials.models import Material


class Command(BaseCommand):
    help = 'Carrega dados fakes de demonstração para o portal do Prof. Toni Coimbra.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            default='professordash123',
            help='Senha usada para usuários demo criados pelo seed.',
        )
        parser.add_argument(
            '--reset-passwords',
            action='store_true',
            help='Redefine a senha dos usuários demo existentes.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.password = options['password']
        self.reset_passwords = options['reset_passwords']
        self.now = timezone.now()

        professor = self.seed_professor()
        disciplinas = self.seed_catalog()
        students = self.seed_students()
        turmas = self.seed_turmas(professor, disciplinas)
        self.seed_enrollments(turmas, students)
        publicadas = self.seed_published_lessons(turmas, disciplinas)
        materials = self.seed_materials(turmas, publicadas, professor)
        atividades = self.seed_activities(turmas, publicadas, materials)
        self.seed_progress(publicadas, students)
        self.seed_submissions(atividades, students, professor)

        self.stdout.write(self.style.SUCCESS('Seed demo concluído.'))
        self.stdout.write(
            'Login professor: professor@professordash.local '
            f'/ senha: {self.password}'
        )
        self.stdout.write(
            'Login aluno exemplo: ana.lima@professordash.local '
            f'/ senha: {self.password}'
        )

    def seed_professor(self):
        professor = self.upsert_user(
            email='professor@professordash.local',
            nome_completo='Prof. Toni Coimbra',
            role=User.Role.PROFESSOR,
        )
        profile, _ = ProfessorProfile.objects.get_or_create(user=professor)
        profile.seed_registration = 'SEED-PR-0001'
        profile.disciplines = 'Inteligência Artificial, Programação Front-End'
        profile.save(update_fields=['seed_registration', 'disciplines', 'updated_at'])
        return professor

    def seed_catalog(self):
        ai, _ = Disciplina.objects.update_or_create(
            slug='inteligencia-artificial',
            defaults={
                'label': 'Inteligência Artificial',
                'serie': '3º ano',
                'status': 'aprovada',
            },
        )
        frontend, _ = Disciplina.objects.update_or_create(
            slug='programacao-front-end',
            defaults={
                'label': 'Programação Front-End',
                'serie': '2º ano',
                'status': 'aprovada',
            },
        )

        trilha_ai, _ = Trilha.objects.update_or_create(
            disciplina=ai,
            slug='fundamentos-de-ia',
            defaults={'label': 'Fundamentos de IA'},
        )
        trilha_frontend, _ = Trilha.objects.update_or_create(
            disciplina=frontend,
            slug='interfaces-web',
            defaults={'label': 'Interfaces Web'},
        )

        lessons = [
            (
                ai,
                trilha_ai,
                1,
                'fundamentos-de-ia',
                'Fundamentos de Inteligência Artificial',
                'Como máquinas aprendem padrões a partir de dados.',
            ),
            (
                ai,
                trilha_ai,
                2,
                'prompt-engineering',
                'Prompt Engineering',
                'Como pedir bem para obter respostas melhores.',
            ),
            (
                ai,
                trilha_ai,
                3,
                'etica-em-ia',
                'Ética em Inteligência Artificial',
                'Vieses, transparência e responsabilidade no uso da IA.',
            ),
            (
                frontend,
                trilha_frontend,
                1,
                'html-semantico',
                'HTML Semântico',
                'Estrutura significativa para páginas acessíveis.',
            ),
            (
                frontend,
                trilha_frontend,
                2,
                'css-responsivo',
                'CSS Responsivo',
                'Layouts que funcionam bem no celular e no desktop.',
            ),
        ]

        aulas = {}
        for disciplina, trilha, ordem, slug, titulo, tema in lessons:
            aula, _ = Aula.objects.update_or_create(
                disciplina=disciplina,
                trilha=trilha,
                ordem=ordem,
                slug=slug,
                defaults={
                    'titulo': titulo,
                    'tema': tema,
                    'objetivos': [
                        'Compreender os conceitos centrais da aula.',
                        'Aplicar o conteúdo em uma atividade prática.',
                    ],
                    'prerequisitos': [],
                    'modo_origem': 'seed_demo',
                    'conteudo_md': f'# {titulo}\n\n{tema}',
                    'conteudo_html': self.lesson_html(titulo, tema),
                    'status': Aula.Status.APROVADA,
                    'versao': 'seed-demo-1',
                    'atualizado_em': self.now,
                    'source_path': 'seed_demo',
                },
            )
            aulas[slug] = aula

        return {
            'ai': ai,
            'frontend': frontend,
            'aulas': aulas,
        }

    def seed_students(self):
        rows = [
            ('ana.lima@professordash.local', 'Ana Lima', '2026001'),
            ('bruno.reis@professordash.local', 'Bruno Reis', '2026002'),
            ('carla.souza@professordash.local', 'Carla Souza', '2026003'),
            ('diego.martins@professordash.local', 'Diego Martins', '2026004'),
            ('elisa.rocha@professordash.local', 'Elisa Rocha', '2026005'),
            ('felipe.costa@professordash.local', 'Felipe Costa', '2026006'),
            ('giovana.alves@professordash.local', 'Giovana Alves', '2026007'),
            ('hugo.pereira@professordash.local', 'Hugo Pereira', '2026008'),
        ]
        students = []
        for email, name, registration in rows:
            student = self.upsert_user(
                email=email,
                nome_completo=name,
                role=User.Role.ALUNO,
            )
            profile, _ = AlunoProfile.objects.get_or_create(user=student)
            profile.school_registration = registration
            profile.grade = '3º ano'
            profile.responsible_name = f'Responsável de {name}'
            profile.birth_date = timezone.localdate().replace(year=2008)
            profile.save(
                update_fields=[
                    'school_registration',
                    'grade',
                    'responsible_name',
                    'birth_date',
                    'updated_at',
                ]
            )
            students.append(student)
        return students

    def seed_turmas(self, professor, disciplinas):
        turma_ai, _ = Turma.objects.update_or_create(
            nome='3º DS · Matutino',
            ano_letivo=timezone.localdate().year,
            professor=professor,
            defaults={
                'disciplina': disciplinas['ai'],
                'serie': '3º ano',
                'ativa': True,
            },
        )
        turma_frontend, _ = Turma.objects.update_or_create(
            nome='2º DS · Vespertino',
            ano_letivo=timezone.localdate().year,
            professor=professor,
            defaults={
                'disciplina': disciplinas['frontend'],
                'serie': '2º ano',
                'ativa': True,
            },
        )
        return {
            'ai': turma_ai,
            'frontend': turma_frontend,
        }

    def seed_enrollments(self, turmas, students):
        for student in students:
            Matricula.objects.update_or_create(
                turma=turmas['ai'],
                aluno=student,
                defaults={
                    'data_matricula': timezone.localdate(),
                    'status': Matricula.Status.ATIVA,
                },
            )
        for student in students[:5]:
            Matricula.objects.update_or_create(
                turma=turmas['frontend'],
                aluno=student,
                defaults={
                    'data_matricula': timezone.localdate(),
                    'status': Matricula.Status.ATIVA,
                },
            )

    def seed_published_lessons(self, turmas, disciplinas):
        aulas = disciplinas['aulas']
        specs = [
            (
                'ai-1',
                turmas['ai'],
                aulas['fundamentos-de-ia'],
                1,
                self.now - timezone.timedelta(days=12),
                True,
            ),
            (
                'ai-2',
                turmas['ai'],
                aulas['prompt-engineering'],
                2,
                self.now - timezone.timedelta(days=6),
                True,
            ),
            (
                'ai-3',
                turmas['ai'],
                aulas['etica-em-ia'],
                3,
                self.now + timezone.timedelta(days=2),
                True,
            ),
            (
                'front-1',
                turmas['frontend'],
                aulas['html-semantico'],
                1,
                self.now - timezone.timedelta(days=8),
                True,
            ),
            (
                'front-2',
                turmas['frontend'],
                aulas['css-responsivo'],
                2,
                self.now - timezone.timedelta(days=1),
                True,
            ),
        ]
        publicadas = {}
        for key, turma, aula, ordem, disponivel_em, publicada in specs:
            item, _ = AulaPublicada.objects.update_or_create(
                turma=turma,
                aula=aula,
                defaults={
                    'ordem_na_turma': ordem,
                    'disponivel_em': disponivel_em,
                    'publicada': publicada,
                },
            )
            publicadas[key] = item
        return publicadas

    def seed_materials(self, turmas, publicadas, professor):
        material_prompt, _ = Material.objects.update_or_create(
            turma=turmas['ai'],
            titulo='Guia rápido de prompts',
            defaults={
                'aula_publicada': publicadas['ai-2'],
                'descricao': 'Resumo de apoio para a atividade de prompt eficaz.',
                'link_externo': 'https://prof.tonicoimbra.com',
                'tipo': Material.Tipo.LINK,
                'enviado_por': professor,
            },
        )
        material_frontend, _ = Material.objects.update_or_create(
            turma=turmas['frontend'],
            titulo='Checklist de HTML semântico',
            defaults={
                'aula_publicada': publicadas['front-1'],
                'descricao': 'Lista de conferência para revisar a página.',
                'link_externo': 'https://developer.mozilla.org/pt-BR/',
                'tipo': Material.Tipo.LINK,
                'enviado_por': professor,
            },
        )
        return {
            'prompt': material_prompt,
            'frontend': material_frontend,
        }

    def seed_activities(self, turmas, publicadas, materials):
        atividade_prompt = self.upsert_activity(
            turma=turmas['ai'],
            aula_publicada=publicadas['ai-2'],
            titulo='Exercício: prompt eficaz',
            enunciado=(
                'Crie um prompt para pedir a uma IA um plano de estudo '
                'para uma prova técnica. Explique por que ele é claro.'
            ),
            prazo=self.now + timezone.timedelta(days=2),
            pontuacao_max=Decimal('10.00'),
            anexos=[materials['prompt']],
        )
        atividade_mapa = self.upsert_activity(
            turma=turmas['ai'],
            aula_publicada=publicadas['ai-1'],
            titulo='Mapa mental: fundamentos de IA',
            enunciado='Organize os principais conceitos da aula em um mapa mental.',
            prazo=self.now - timezone.timedelta(days=1),
            pontuacao_max=Decimal('8.00'),
            anexos=[],
        )
        atividade_portfolio = self.upsert_activity(
            turma=turmas['frontend'],
            aula_publicada=publicadas['front-1'],
            titulo='Página de portfólio semântica',
            enunciado='Monte uma página pessoal usando tags semânticas do HTML.',
            prazo=self.now + timezone.timedelta(days=5),
            pontuacao_max=Decimal('10.00'),
            anexos=[materials['frontend']],
        )
        return {
            'prompt': atividade_prompt,
            'mapa': atividade_mapa,
            'portfolio': atividade_portfolio,
        }

    def seed_progress(self, publicadas, students):
        progress_specs = [
            (publicadas['ai-1'], students[:7]),
            (publicadas['ai-2'], students[:4]),
            (publicadas['front-1'], students[:5]),
            (publicadas['front-2'], students[:2]),
        ]
        for publicada, selected_students in progress_specs:
            for index, student in enumerate(selected_students, start=1):
                progresso, _ = ProgressoAula.objects.get_or_create(
                    aluno=student,
                    aula_publicada=publicada,
                )
                progresso.visto_em = self.now - timezone.timedelta(days=index)
                progresso.concluido = True
                progresso.concluido_em = progresso.visto_em + timezone.timedelta(hours=1)
                progresso.save(
                    update_fields=[
                        'visto_em',
                        'concluido',
                        'concluido_em',
                        'updated_at',
                    ]
                )

    def seed_submissions(self, atividades, students, professor):
        self.upsert_submission(
            atividades['prompt'],
            students[0],
            'Prompt com objetivo, contexto, formato de saída e critérios.',
            self.now - timezone.timedelta(hours=8),
            Entrega.Status.CORRIGIDA,
            nota=Decimal('9.50'),
            feedback='Resposta clara e bem estruturada.',
            professor=professor,
        )
        self.upsert_submission(
            atividades['prompt'],
            students[1],
            'Meu prompt pede um cronograma de estudos com revisão diária.',
            self.now - timezone.timedelta(hours=3),
            Entrega.Status.ENTREGUE,
        )
        self.upsert_submission(
            atividades['prompt'],
            students[2],
            'Foquei no formato de tabela e exemplos de exercícios.',
            self.now - timezone.timedelta(hours=2),
            Entrega.Status.ENTREGUE,
        )
        self.upsert_submission(
            atividades['mapa'],
            students[0],
            'Mapa mental com dados, modelo, treino, inferência e avaliação.',
            self.now - timezone.timedelta(days=2),
            Entrega.Status.CORRIGIDA,
            nota=Decimal('8.00'),
            feedback='Mapa completo e bem conectado.',
            professor=professor,
        )
        self.upsert_submission(
            atividades['mapa'],
            students[3],
            'Conceitos principais organizados por exemplos práticos.',
            self.now - timezone.timedelta(hours=5),
            Entrega.Status.ATRASADA,
        )
        self.upsert_submission(
            atividades['portfolio'],
            students[0],
            'Enviei a página com header, main, section e footer.',
            self.now - timezone.timedelta(days=1),
            Entrega.Status.CORRIGIDA,
            nota=Decimal('9.00'),
            feedback='Boa semântica e boa hierarquia de conteúdo.',
            professor=professor,
        )
        self.upsert_submission(
            atividades['portfolio'],
            students[4],
            'Primeira versão do portfólio com navegação e cards.',
            self.now - timezone.timedelta(hours=1),
            Entrega.Status.ENTREGUE,
        )

    def upsert_user(self, email, nome_completo, role):
        user, created = User.objects.update_or_create(
            email=email,
            defaults={
                'nome_completo': nome_completo,
                'role': role,
                'is_active': True,
            },
        )
        if created or self.reset_passwords or not user.has_usable_password():
            user.set_password(self.password)
            user.save(update_fields=['password', 'updated_at'])
        return user

    def upsert_activity(
        self,
        turma,
        aula_publicada,
        titulo,
        enunciado,
        prazo,
        pontuacao_max,
        anexos,
    ):
        atividade, _ = Atividade.objects.update_or_create(
            turma=turma,
            titulo=titulo,
            defaults={
                'aula_publicada': aula_publicada,
                'enunciado': enunciado,
                'prazo': prazo,
                'pontuacao_max': pontuacao_max,
                'permite_entrega_atrasada': True,
                'publicada': True,
            },
        )
        atividade.anexos.set(anexos)
        return atividade

    def upsert_submission(
        self,
        atividade,
        aluno,
        texto_resposta,
        data_entrega,
        status,
        nota=None,
        feedback='',
        professor=None,
    ):
        defaults = {
            'texto_resposta': texto_resposta,
            'data_entrega': data_entrega,
            'status': status,
            'checked': status == Entrega.Status.CORRIGIDA,
            'nota': nota,
            'feedback': feedback,
            'corrigido_por': professor if status == Entrega.Status.CORRIGIDA else None,
            'corrigido_em': (
                min(self.now, data_entrega + timezone.timedelta(hours=2))
                if status == Entrega.Status.CORRIGIDA
                else None
            ),
        }
        Entrega.objects.update_or_create(
            atividade=atividade,
            aluno=aluno,
            defaults=defaults,
        )

    def lesson_html(self, title, theme):
        return (
            f'<h2>{title}</h2>'
            f'<p>{theme}</p>'
            '<div class="lesson-callout lesson-callout-conceito">'
            '<div class="lesson-callout-title">Conceito-chave</div>'
            '<p>Esta aula foi criada pelo seed demo para validar a jornada.</p>'
            '</div>'
        )
