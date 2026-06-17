from django.urls import path

from .views import (
    AlunoAtividadeListView,
    AlunoEntregaView,
    AtividadeCreateView,
    AtividadeDeleteView,
    AtividadeEntregasView,
    AtividadeListView,
    AtividadeUpdateView,
    CorrecaoView,
    EntregaArquivoDownloadView,
)

app_name = 'activities'

urlpatterns = [
    # Aluno
    path(
        'aluno/turmas/<int:turma_pk>/',
        AlunoAtividadeListView.as_view(),
        name='aluno_atividade_list',
    ),
    path('aluno/<int:pk>/', AlunoEntregaView.as_view(), name='aluno_entrega'),
    # Professor
    path(
        'turmas/<int:turma_pk>/',
        AtividadeListView.as_view(),
        name='atividade_list',
    ),
    path(
        'turmas/<int:turma_pk>/nova/',
        AtividadeCreateView.as_view(),
        name='atividade_create',
    ),
    path('<int:pk>/editar/', AtividadeUpdateView.as_view(), name='atividade_update'),
    path('<int:pk>/excluir/', AtividadeDeleteView.as_view(), name='atividade_delete'),
    path(
        '<int:pk>/entregas/',
        AtividadeEntregasView.as_view(),
        name='atividade_entregas',
    ),
    path(
        'entregas/<int:pk>/corrigir/',
        CorrecaoView.as_view(),
        name='correcao',
    ),
    path(
        'arquivos/<int:pk>/baixar/',
        EntregaArquivoDownloadView.as_view(),
        name='entrega_arquivo_download',
    ),
]
