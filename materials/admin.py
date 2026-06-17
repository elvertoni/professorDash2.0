from django.contrib import admin

from .models import Material


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = (
        'titulo',
        'tipo',
        'turma',
        'aula_publicada',
        'enviado_por',
        'updated_at',
    )
    list_filter = ('tipo', 'turma__disciplina')
    search_fields = ('titulo', 'descricao', 'turma__nome')
    autocomplete_fields = ('turma', 'aula_publicada', 'enviado_por')
    readonly_fields = ('created_at', 'updated_at')
