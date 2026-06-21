from django.contrib import admin

from .models import Atividade, AtividadeCheck


class AtividadeCheckInline(admin.TabularInline):
    model = AtividadeCheck
    extra = 0
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Atividade)
class AtividadeAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'turma', 'data')
    list_filter = ('turma__disciplina', 'turma')
    search_fields = ('titulo', 'turma__nome')
    autocomplete_fields = ('turma',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = (AtividadeCheckInline,)


@admin.register(AtividadeCheck)
class AtividadeCheckAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'atividade', 'feito', 'feito_em')
    list_filter = ('feito', 'atividade__turma')
    search_fields = ('aluno__nome_completo', 'atividade__titulo')
    autocomplete_fields = ('atividade', 'aluno')
    readonly_fields = ('created_at', 'updated_at')
