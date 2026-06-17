from django.conf import settings
from django.db import models
from django.db.models import Q

from base.models import TimeStampedModel


class Notificacao(TimeStampedModel):
    class Tipo(models.TextChoices):
        AULA = 'aula', 'Aula'
        ATIVIDADE = 'atividade', 'Atividade'
        PRAZO = 'prazo', 'Prazo'
        CORRECAO = 'correcao', 'Correção'

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='usuário',
        on_delete=models.CASCADE,
        related_name='notificacoes',
    )
    titulo = models.CharField('título', max_length=180)
    mensagem = models.TextField('mensagem')
    link = models.CharField('link', max_length=500, blank=True)
    lida = models.BooleanField('lida', default=False)
    tipo = models.CharField('tipo', max_length=20, choices=Tipo.choices)
    dedupe_key = models.CharField(
        'chave de deduplicação',
        max_length=180,
        blank=True,
        editable=False,
    )

    class Meta:
        verbose_name = 'notificação'
        verbose_name_plural = 'notificações'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['usuario', 'tipo', 'dedupe_key'],
                condition=~Q(dedupe_key=''),
                name='unique_notificacao_dedupe_por_usuario',
            ),
        ]
        indexes = [
            models.Index(fields=['usuario', 'lida', '-created_at']),
            models.Index(fields=['usuario', 'tipo']),
        ]

    def __str__(self):
        return f'{self.titulo} · {self.usuario}'

    def mark_read(self):
        if self.lida:
            return
        self.lida = True
        self.save(update_fields=['lida', 'updated_at'])
