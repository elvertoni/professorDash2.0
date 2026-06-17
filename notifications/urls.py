from django.urls import path

from .views import (
    NotificacaoListView,
    NotificacaoMarkAllReadView,
    NotificacaoMarkReadView,
)

app_name = 'notifications'

urlpatterns = [
    path('', NotificacaoListView.as_view(), name='list'),
    path('marcar-todas/', NotificacaoMarkAllReadView.as_view(), name='mark_all_read'),
    path('<int:pk>/marcar-lida/', NotificacaoMarkReadView.as_view(), name='mark_read'),
]
