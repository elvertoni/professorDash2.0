from django.urls import path

from .views import (
    AlunoMaterialListView,
    MaterialCreateView,
    MaterialDeleteView,
    MaterialDownloadView,
    MaterialListView,
    MaterialUpdateView,
)

app_name = 'materials'

urlpatterns = [
    # Aluno
    path(
        'aluno/turmas/<int:turma_pk>/',
        AlunoMaterialListView.as_view(),
        name='aluno_material_list',
    ),
    # Download protegido (professor ou aluno da turma)
    path('<int:pk>/baixar/', MaterialDownloadView.as_view(), name='material_download'),
    # Professor
    path(
        'turmas/<int:turma_pk>/',
        MaterialListView.as_view(),
        name='material_list',
    ),
    path(
        'turmas/<int:turma_pk>/novo/',
        MaterialCreateView.as_view(),
        name='material_create',
    ),
    path('<int:pk>/editar/', MaterialUpdateView.as_view(), name='material_update'),
    path('<int:pk>/excluir/', MaterialDeleteView.as_view(), name='material_delete'),
]
