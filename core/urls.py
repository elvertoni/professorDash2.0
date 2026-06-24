"""URL configuration for Prof. Toni Coimbra (core)."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.conf.urls.static import static

from base.views import HomeView, health, public_media

urlpatterns = [
    path('admin/', admin.site.urls),
    path('conta/', include('accounts.urls')),
    path('catalogo/', include('catalog.urls')),
    path('turmas/', include('classroom.urls')),
    path('atividades/', include('activities.urls')),
    path('materiais/', include('materials.urls')),
    path('notificacoes/', include('notifications.urls')),
    path('health/', health, name='health'),
    path('media/<path:path>', public_media, name='public_media'),
    path('', HomeView.as_view(), name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
