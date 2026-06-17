from django.contrib import admin

from .models import Notificacao


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'usuario', 'tipo', 'lida', 'created_at')
    list_filter = ('tipo', 'lida', 'created_at')
    search_fields = ('titulo', 'mensagem', 'usuario__email', 'usuario__nome_completo')
    readonly_fields = ('dedupe_key', 'created_at', 'updated_at')
    ordering = ('-created_at',)
