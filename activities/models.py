import os
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from base.models import TimeStampedModel
from base.storage import protected_storage
from classroom.models import AulaPublicada, Turma


MAX_SUBMISSION_FILE_SIZE = 20 * 1024 * 1024
ALLOWED_SUBMISSION_EXTENSIONS = {
    'csv',
    'doc',
    'docx',
    'gif',
    'jpeg',
    'jpg',
    'md',
    'odp',
    'ods',
    'odt',
    'pdf',
    'png',
    'ppt',
    'pptx',
    'txt',
    'webp',
    'xls',
    'xlsx',
    'zip',
}


def validate_submission_file(upload):
    if not upload:
        return

    extension = Path(upload.name).suffix.lower().lstrip('.')
    if extension not in ALLOWED_SUBMISSION_EXTENSIONS:
        raise ValidationError(
            'Tipo de arquivo não permitido para entregas de atividade.'
        )

    if getattr(upload, 'size', 0) > MAX_SUBMISSION_FILE_SIZE:
        raise ValidationError('O arquivo deve ter no máximo 20 MB.')


class Atividade(TimeStampedModel):
    turma = models.ForeignKey(
        Turma,
        verbose_name='turma',
        on_delete=models.CASCADE,
        related_name='atividades',
    )
    aula_publicada = models.ForeignKey(
        AulaPublicada,
        verbose_name='aula publicada',
        on_delete=models.SET_NULL,
        related_name='atividades',
        blank=True,
        null=True,
    )
    titulo = models.CharField('título', max_length=220)
    enunciado = models.TextField('enunciado', blank=True)
    anexos = models.ManyToManyField(
        'materials.Material',
        verbose_name='materiais anexados',
        related_name='atividades',
        blank=True,
    )
    prazo = models.DateTimeField('prazo', blank=True, null=True)
    pontuacao_max = models.DecimalField(
        'pontuação máxima',
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00'),
    )
    permite_entrega_atrasada = models.BooleanField(
        'permite entrega atrasada',
        default=True,
    )
    publicada = models.BooleanField('publicada', default=False)

    class Meta:
        verbose_name = 'atividade'
        verbose_name_plural = 'atividades'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['turma', 'publicada']),
        ]

    def __str__(self):
        return self.titulo

    def clean(self):
        super().clean()
        errors = {}
        if (
            self.turma_id
            and self.aula_publicada_id
            and self.aula_publicada.turma_id != self.turma_id
        ):
            errors['aula_publicada'] = (
                'A aula relacionada precisa pertencer à turma da atividade.'
            )
        if self.pk and self.turma_id:
            invalid_anexos = self.anexos.exclude(turma_id=self.turma_id)
            if invalid_anexos.exists():
                errors['anexos'] = (
                    'Todos os materiais anexados precisam pertencer à turma '
                    'da atividade.'
                )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def validate_anexos_turma(self, anexos=None):
        anexos = self.anexos.all() if anexos is None else anexos
        invalid = [anexo for anexo in anexos if anexo.turma_id != self.turma_id]
        if invalid:
            raise ValidationError(
                {
                    'anexos': (
                        'Todos os materiais anexados precisam pertencer à turma '
                        'da atividade.'
                    )
                }
            )

    @property
    def is_overdue(self):
        return bool(self.prazo and timezone.now() > self.prazo)

    @property
    def aberta_para_entrega(self):
        if not self.publicada:
            return False
        if self.is_overdue and not self.permite_entrega_atrasada:
            return False
        return True


class Entrega(TimeStampedModel):
    class Status(models.TextChoices):
        PENDENTE = 'pendente', 'Pendente'
        ENTREGUE = 'entregue', 'Entregue'
        ATRASADA = 'atrasada', 'Atrasada'
        CORRIGIDA = 'corrigida', 'Corrigida'

    atividade = models.ForeignKey(
        Atividade,
        verbose_name='atividade',
        on_delete=models.CASCADE,
        related_name='entregas',
    )
    aluno = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='aluno',
        on_delete=models.CASCADE,
        related_name='entregas',
        limit_choices_to={'role': 'aluno'},
    )
    texto_resposta = models.TextField('resposta', blank=True)
    data_entrega = models.DateTimeField('data da entrega', blank=True, null=True)
    status = models.CharField(
        'status',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
    )
    nota = models.DecimalField(
        'nota',
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
    )
    feedback = models.TextField('feedback', blank=True)
    corrigido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='corrigido por',
        on_delete=models.SET_NULL,
        related_name='correcoes',
        blank=True,
        null=True,
        limit_choices_to={'role': 'professor'},
    )
    corrigido_em = models.DateTimeField('corrigido em', blank=True, null=True)
    checked = models.BooleanField('corrigida', default=False)

    class Meta:
        verbose_name = 'entrega'
        verbose_name_plural = 'entregas'
        ordering = ['-data_entrega', '-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['atividade', 'aluno'],
                name='unique_entrega_por_atividade_aluno',
            ),
        ]
        indexes = [
            models.Index(fields=['atividade', 'status']),
        ]

    def __str__(self):
        return f'{self.aluno} · {self.atividade}'

    def submit(self, now=None):
        now = now or timezone.now()
        self.data_entrega = now
        prazo = self.atividade.prazo
        if prazo and now > prazo:
            self.status = self.Status.ATRASADA
        else:
            self.status = self.Status.ENTREGUE

    def mark_checked(self, professor, nota, feedback):
        self.nota = nota
        self.feedback = feedback
        self.corrigido_por = professor
        self.corrigido_em = timezone.now()
        self.checked = True
        self.status = self.Status.CORRIGIDA
        self.save()


class EntregaArquivo(TimeStampedModel):
    entrega = models.ForeignKey(
        Entrega,
        verbose_name='entrega',
        on_delete=models.CASCADE,
        related_name='arquivos',
    )
    arquivo = models.FileField(
        'arquivo',
        storage=protected_storage,
        upload_to='entregas/',
    )

    class Meta:
        verbose_name = 'arquivo de entrega'
        verbose_name_plural = 'arquivos de entrega'
        ordering = ['created_at']

    def __str__(self):
        return self.nome

    def clean(self):
        super().clean()
        validate_submission_file(self.arquivo)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def nome(self):
        return os.path.basename(self.arquivo.name)
