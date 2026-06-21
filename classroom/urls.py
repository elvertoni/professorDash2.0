from django.urls import path

from .views import (
    AlunoAulaDetailView,
    AlunoBoletimPdfView,
    AlunoDashboardView,
    AlunoTurmaAulasView,
    AulaPublicadaDeleteView,
    AulaPublicadaManageView,
    AulaPublicadaPreviewView,
    AulaPublicadaReorderView,
    AulaPublicadaToggleView,
    AulaPublicadaUpdateView,
    MatriculaCreateView,
    MatriculaDeleteView,
    MatriculaUpdateView,
    ProfessorDashboardView,
    ProgressoToggleView,
    RegenerateInviteCodeView,
    StudentCsvImportView,
    TurmaBoletimPdfView,
    TurmaCreateView,
    TurmaDeleteView,
    TurmaDetailView,
    TurmaListView,
    TurmaRelatorioCsvView,
    TurmaRelatorioPdfView,
    TurmaSyncAulasView,
    TurmaUpdateView,
)

app_name = 'classroom'

urlpatterns = [
    path('', TurmaListView.as_view(), name='turma_list'),
    path('painel/', ProfessorDashboardView.as_view(), name='professor_dashboard'),
    path('nova/', TurmaCreateView.as_view(), name='turma_create'),
    # Área do aluno (Sprints 4 e 5)
    path('aluno/', AlunoDashboardView.as_view(), name='aluno_dashboard'),
    path(
        'aluno/turmas/<int:turma_pk>/',
        AlunoTurmaAulasView.as_view(),
        name='aluno_turma_aulas',
    ),
    path(
        'aluno/aulas/<int:pk>/',
        AlunoAulaDetailView.as_view(),
        name='aluno_aula_detail',
    ),
    path(
        'aluno/aulas/<int:pk>/concluir/',
        ProgressoToggleView.as_view(),
        name='aluno_aula_toggle',
    ),
    path(
        'aluno/turmas/<int:turma_pk>/boletim.pdf',
        AlunoBoletimPdfView.as_view(),
        name='aluno_boletim_pdf',
    ),
    path('<int:pk>/', TurmaDetailView.as_view(), name='turma_detail'),
    path(
        '<int:pk>/relatorio.pdf',
        TurmaRelatorioPdfView.as_view(),
        name='turma_relatorio_pdf',
    ),
    path(
        '<int:pk>/relatorio.csv',
        TurmaRelatorioCsvView.as_view(),
        name='turma_relatorio_csv',
    ),
    path('<int:pk>/editar/', TurmaUpdateView.as_view(), name='turma_update'),
    path('<int:pk>/excluir/', TurmaDeleteView.as_view(), name='turma_delete'),
    path(
        '<int:pk>/renovar-convite/',
        RegenerateInviteCodeView.as_view(),
        name='turma_regenerate_invite',
    ),
    # Publicação de aulas por turma (Sprint 4)
    path(
        '<int:turma_pk>/aulas/',
        AulaPublicadaManageView.as_view(),
        name='turma_aulas',
    ),
    path(
        '<int:turma_pk>/aulas/sincronizar/',
        TurmaSyncAulasView.as_view(),
        name='turma_aulas_sync',
    ),
    path(
        '<int:turma_pk>/aulas/<int:pk>/editar/',
        AulaPublicadaUpdateView.as_view(),
        name='aula_publicada_update',
    ),
    path(
        '<int:turma_pk>/aulas/<int:pk>/visualizar/',
        AulaPublicadaPreviewView.as_view(),
        name='aula_publicada_preview',
    ),
    path(
        '<int:turma_pk>/aulas/<int:pk>/publicar/',
        AulaPublicadaToggleView.as_view(),
        name='aula_publicada_toggle',
    ),
    path(
        '<int:turma_pk>/aulas/<int:pk>/remover/',
        AulaPublicadaDeleteView.as_view(),
        name='aula_publicada_delete',
    ),
    path(
        '<int:turma_pk>/aulas/<int:pk>/reordenar/',
        AulaPublicadaReorderView.as_view(),
        name='aula_publicada_reorder',
    ),
    path(
        '<int:turma_pk>/alunos/novo/',
        MatriculaCreateView.as_view(),
        name='matricula_create',
    ),
    path(
        '<int:turma_pk>/alunos/importar/',
        StudentCsvImportView.as_view(),
        name='matricula_import',
    ),
    path(
        '<int:turma_pk>/alunos/<int:pk>/editar/',
        MatriculaUpdateView.as_view(),
        name='matricula_update',
    ),
    path(
        '<int:turma_pk>/alunos/<int:pk>/desmatricular/',
        MatriculaDeleteView.as_view(),
        name='matricula_delete',
    ),
    path(
        '<int:turma_pk>/alunos/<int:pk>/boletim.pdf',
        TurmaBoletimPdfView.as_view(),
        name='turma_boletim_pdf',
    ),
]
