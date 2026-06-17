from django.contrib import admin

from .models import AulaPublicada, Matricula, ProgressoAula, Turma


class MatriculaInline(admin.TabularInline):
    model = Matricula
    extra = 0
    autocomplete_fields = ('aluno',)
    fields = ('aluno', 'data_matricula', 'status')


@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = (
        'nome',
        'disciplina',
        'serie',
        'ano_letivo',
        'professor',
        'codigo_convite',
        'ativa',
    )
    list_filter = ('ativa', 'ano_letivo', 'disciplina', 'serie')
    search_fields = (
        'nome',
        'codigo_convite',
        'professor__email',
        'professor__nome_completo',
        'disciplina__label',
    )
    autocomplete_fields = ('disciplina', 'professor')
    readonly_fields = ('codigo_convite', 'created_at', 'updated_at')
    inlines = (MatriculaInline,)


@admin.register(Matricula)
class MatriculaAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'turma', 'data_matricula', 'status', 'updated_at')
    list_filter = ('status', 'turma__ano_letivo', 'turma__disciplina')
    search_fields = (
        'aluno__email',
        'aluno__nome_completo',
        'turma__nome',
        'turma__codigo_convite',
    )
    autocomplete_fields = ('turma', 'aluno')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AulaPublicada)
class AulaPublicadaAdmin(admin.ModelAdmin):
    list_display = (
        'aula',
        'turma',
        'ordem_na_turma',
        'disponivel_em',
        'publicada',
    )
    list_filter = ('publicada', 'turma__ano_letivo', 'turma__disciplina')
    search_fields = (
        'aula__titulo',
        'turma__nome',
        'turma__codigo_convite',
    )
    autocomplete_fields = ('turma', 'aula')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ProgressoAula)
class ProgressoAulaAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'aula_publicada', 'concluido', 'concluido_em', 'visto_em')
    list_filter = ('concluido',)
    search_fields = (
        'aluno__email',
        'aluno__nome_completo',
        'aula_publicada__aula__titulo',
    )
    autocomplete_fields = ('aluno', 'aula_publicada')
    readonly_fields = ('created_at', 'updated_at')
