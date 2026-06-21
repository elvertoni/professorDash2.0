from django.urls import path

from .views import AcervoGithubImportView, AulaDetailView, AulaListView

app_name = 'catalog'

urlpatterns = [
    path('', AulaListView.as_view(), name='aula_list'),
    path(
        'importar/github/',
        AcervoGithubImportView.as_view(),
        name='acervo_import_github',
    ),
    path('aulas/<int:pk>/', AulaDetailView.as_view(), name='aula_detail'),
]
