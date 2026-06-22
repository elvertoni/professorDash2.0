from django.contrib import admin
from django.utils.html import format_html

from .models import Aula, Disciplina, Trilha


@admin.register(Disciplina)
class DisciplinaAdmin(admin.ModelAdmin):
    list_display = ('label', 'slug', 'serie', 'status', 'updated_at')
    list_filter = ('status', 'serie')
    search_fields = ('label', 'slug')
    prepopulated_fields = {'slug': ('label',)}
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Trilha)
class TrilhaAdmin(admin.ModelAdmin):
    list_display = ('label', 'slug', 'disciplina', 'updated_at')
    list_filter = ('disciplina',)
    search_fields = ('label', 'slug', 'disciplina__label')
    autocomplete_fields = ('disciplina',)
    prepopulated_fields = {'slug': ('label',)}
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Aula)
class AulaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'disciplina', 'trilha', 'ordem', 'status', 'versao')
    list_filter = ('status', 'disciplina', 'trilha')
    search_fields = ('titulo', 'tema', 'slug', 'source_path')
    autocomplete_fields = ('disciplina', 'trilha')
    readonly_fields = ('created_at', 'updated_at', 'cover_preview')

    @admin.display(description='prévia da capa')
    def cover_preview(self, obj):
        if not obj.imagem:
            return '—'
        return format_html(
            '<img src="{}" style="max-width:320px;height:auto;border-radius:8px;">',
            obj.imagem.url,
        )
