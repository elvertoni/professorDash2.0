from django.db import models
from django.urls import reverse

from base.models import TimeStampedModel


class Disciplina(TimeStampedModel):
    slug = models.SlugField('slug', max_length=120, unique=True)
    label = models.CharField('nome', max_length=180)
    serie = models.CharField('série', max_length=80, blank=True)
    status = models.CharField('status', max_length=40, blank=True)

    class Meta:
        verbose_name = 'disciplina'
        verbose_name_plural = 'disciplinas'
        ordering = ['label']

    def __str__(self):
        return self.label


class Trilha(TimeStampedModel):
    disciplina = models.ForeignKey(
        Disciplina,
        verbose_name='disciplina',
        on_delete=models.CASCADE,
        related_name='trilhas',
    )
    slug = models.SlugField('slug', max_length=120)
    label = models.CharField('nome', max_length=180)

    class Meta:
        verbose_name = 'trilha'
        verbose_name_plural = 'trilhas'
        ordering = ['disciplina__label', 'label']
        constraints = [
            models.UniqueConstraint(
                fields=['disciplina', 'slug'],
                name='unique_trilha_por_disciplina',
            ),
        ]

    def __str__(self):
        return f'{self.disciplina} · {self.label}'


class Aula(TimeStampedModel):
    class Status(models.TextChoices):
        APROVADA = 'aprovada', 'Aprovada'
        PLANEJADA = 'planejada', 'Planejada'
        RASCUNHO = 'rascunho', 'Rascunho'
        ARQUIVADA = 'arquivada', 'Arquivada'

    disciplina = models.ForeignKey(
        Disciplina,
        verbose_name='disciplina',
        on_delete=models.PROTECT,
        related_name='aulas',
    )
    trilha = models.ForeignKey(
        Trilha,
        verbose_name='trilha',
        on_delete=models.PROTECT,
        related_name='aulas',
    )
    ordem = models.PositiveIntegerField('ordem')
    slug = models.SlugField('slug', max_length=160)
    titulo = models.CharField('título', max_length=220)
    tema = models.CharField('tema', max_length=220, blank=True)
    objetivos = models.JSONField('objetivos', default=list, blank=True)
    prerequisitos = models.JSONField('pré-requisitos', default=list, blank=True)
    modo_origem = models.CharField('modo de origem', max_length=80, blank=True)
    conteudo_html = models.TextField('conteúdo HTML', blank=True)
    conteudo_md = models.TextField('conteúdo Markdown', blank=True)
    html_standalone = models.FileField(
        'HTML standalone',
        upload_to='catalog/html/',
        blank=True,
        null=True,
    )
    status = models.CharField(
        'status',
        max_length=40,
        choices=Status.choices,
        default=Status.APROVADA,
    )
    versao = models.CharField('versão', max_length=80, blank=True)
    atualizado_em = models.DateTimeField('atualizado em na origem', blank=True, null=True)
    source_path = models.TextField('caminho de origem', blank=True)

    class Meta:
        verbose_name = 'aula'
        verbose_name_plural = 'aulas'
        ordering = ['disciplina__label', 'trilha__label', 'ordem', 'titulo']
        constraints = [
            models.UniqueConstraint(
                fields=['disciplina', 'trilha', 'ordem', 'slug'],
                name='unique_aula_canonica',
            ),
        ]
        indexes = [
            models.Index(fields=['status', 'disciplina', 'trilha']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return f'{self.ordem:02d} · {self.titulo}'

    def get_absolute_url(self):
        return reverse('catalog:aula_detail', kwargs={'pk': self.pk})
