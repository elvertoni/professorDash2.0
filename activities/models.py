from django.conf import settings
from django.db import models

from base.models import TimeStampedModel
from classroom.models import Turma


class Atividade(TimeStampedModel):
    '''Item de controle do professor (ex.: "Caderno U1"). Não é entrega.'''

    turma = models.ForeignKey(
        Turma,
        verbose_name='turma',
        on_delete=models.CASCADE,
        related_name='atividades',
    )
    titulo = models.CharField('título', max_length=220)
    descricao = models.TextField('descrição', blank=True)
    data = models.DateField('data', blank=True, null=True)

    class Meta:
        verbose_name = 'atividade'
        verbose_name_plural = 'atividades'
        ordering = ['-data', '-created_at']
        indexes = [
            models.Index(fields=['turma']),
        ]

    def __str__(self):
        return self.titulo


class AtividadeCheck(TimeStampedModel):
    '''Marcação por aluno (feito/não feito) de uma atividade — estilo Notion.'''

    atividade = models.ForeignKey(
        Atividade,
        verbose_name='atividade',
        on_delete=models.CASCADE,
        related_name='checks',
    )
    aluno = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='aluno',
        on_delete=models.CASCADE,
        related_name='atividade_checks',
        limit_choices_to={'role': 'aluno'},
    )
    feito = models.BooleanField('feito', default=False)
    feito_em = models.DateTimeField('feito em', blank=True, null=True)
    observacao = models.CharField('observação', max_length=280, blank=True)

    class Meta:
        verbose_name = 'check de atividade'
        verbose_name_plural = 'checks de atividade'
        ordering = ['aluno__nome_completo']
        constraints = [
            models.UniqueConstraint(
                fields=['atividade', 'aluno'],
                name='unique_check_por_atividade_aluno',
            ),
        ]
        indexes = [
            models.Index(fields=['atividade', 'feito']),
        ]

    def __str__(self):
        marca = '✓' if self.feito else '—'
        return f'{self.aluno} · {self.atividade} · {marca}'
