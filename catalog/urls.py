from django.urls import path

from .views import AulaDetailView, AulaListView

app_name = 'catalog'

urlpatterns = [
    path('', AulaListView.as_view(), name='aula_list'),
    path('aulas/<int:pk>/', AulaDetailView.as_view(), name='aula_detail'),
]
