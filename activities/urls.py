from django.urls import path

from .views import (
    AtividadeChecksView,
    AtividadeCreateView,
    AtividadeDeleteView,
    AtividadeListView,
    AtividadeUpdateView,
)

app_name = 'activities'

urlpatterns = [
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
    path('<int:pk>/checks/', AtividadeChecksView.as_view(), name='atividade_checks'),
]
