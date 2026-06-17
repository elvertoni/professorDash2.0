from django.contrib import admin

from .models import Atividade, Entrega, EntregaArquivo


class EntregaArquivoInline(admin.TabularInline):
    model = EntregaArquivo
    extra = 0
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Atividade)
class AtividadeAdmin(admin.ModelAdmin):
    list_display = (
        'titulo',
        'turma',
        'prazo',
        'pontuacao_max',
        'permite_entrega_atrasada',
        'publicada',
    )
    list_filter = ('publicada', 'permite_entrega_atrasada', 'turma__disciplina')
    search_fields = ('titulo', 'enunciado', 'turma__nome')
    autocomplete_fields = ('turma', 'aula_publicada')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    list_display = (
        'aluno',
        'atividade',
        'status',
        'nota',
        'checked',
        'data_entrega',
        'corrigido_em',
    )
    list_filter = ('status', 'checked', 'atividade__turma')
    search_fields = (
        'aluno__email',
        'aluno__nome_completo',
        'atividade__titulo',
    )
    autocomplete_fields = ('atividade', 'aluno', 'corrigido_por')
    readonly_fields = ('created_at', 'updated_at')
    inlines = (EntregaArquivoInline,)
