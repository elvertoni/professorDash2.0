"""URL configuration for ProfessorDash (core)."""

from django.contrib import admin
from django.urls import include, path

from base.views import HomeView, health

urlpatterns = [
    path('admin/', admin.site.urls),
    path('conta/', include('accounts.urls')),
    path('catalogo/', include('catalog.urls')),
    path('turmas/', include('classroom.urls')),
    path('atividades/', include('activities.urls')),
    path('materiais/', include('materials.urls')),
    path('notificacoes/', include('notifications.urls')),
    path('health/', health, name='health'),
    path('', HomeView.as_view(), name='home'),
]
