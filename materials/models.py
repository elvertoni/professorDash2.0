import os
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from base.models import TimeStampedModel
from base.storage import protected_storage
from classroom.models import AulaPublicada, Turma


MAX_MATERIAL_FILE_SIZE = 25 * 1024 * 1024
ALLOWED_MATERIAL_EXTENSIONS = {
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


def validate_material_file(upload):
    if not upload:
        return

    extension = Path(upload.name).suffix.lower().lstrip('.')
    if extension not in ALLOWED_MATERIAL_EXTENSIONS:
        raise ValidationError(
            'Tipo de arquivo não permitido para materiais da turma.'
        )

    if getattr(upload, 'size', 0) > MAX_MATERIAL_FILE_SIZE:
        raise ValidationError('O arquivo deve ter no máximo 25 MB.')


class Material(TimeStampedModel):
    class Tipo(models.TextChoices):
        PDF = 'pdf', 'PDF'
        SLIDE = 'slide', 'Slide'
        LINK = 'link', 'Link'
        VIDEO = 'video', 'Vídeo'
        OUTRO = 'outro', 'Outro'

    turma = models.ForeignKey(
        Turma,
        verbose_name='turma',
        on_delete=models.CASCADE,
        related_name='materiais',
        blank=True,
        null=True,
    )
    aula_publicada = models.ForeignKey(
        AulaPublicada,
        verbose_name='aula publicada',
        on_delete=models.SET_NULL,
        related_name='materiais',
        blank=True,
        null=True,
    )
    titulo = models.CharField('título', max_length=220)
    descricao = models.TextField('descrição', blank=True)
    arquivo = models.FileField(
        'arquivo',
        storage=protected_storage,
        upload_to='materiais/',
        blank=True,
    )
    link_externo = models.URLField('link externo', blank=True)
    tipo = models.CharField(
        'tipo',
        max_length=20,
        choices=Tipo.choices,
        default=Tipo.OUTRO,
    )
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='enviado por',
        on_delete=models.SET_NULL,
        related_name='materiais_enviados',
        blank=True,
        null=True,
        limit_choices_to={'role': 'professor'},
    )

    class Meta:
        verbose_name = 'material'
        verbose_name_plural = 'materiais'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['turma', 'aula_publicada']),
        ]

    def __str__(self):
        return self.titulo

    def clean(self):
        super().clean()
        if not self.turma and not self.aula_publicada:
            raise ValidationError(
                'Informe a turma ou a aula publicada à qual o material pertence.'
            )
        if (
            self.turma_id
            and self.aula_publicada_id
            and self.aula_publicada.turma_id != self.turma_id
        ):
            raise ValidationError(
                {
                    'aula_publicada': (
                        'A aula relacionada precisa pertencer à mesma turma '
                        'do material.'
                    )
                }
            )
        if not self.arquivo and not self.link_externo:
            raise ValidationError('Anexe um arquivo ou informe um link externo.')
        validate_material_file(self.arquivo)

    def save(self, *args, **kwargs):
        if self.aula_publicada and not self.turma_id:
            self.turma = self.aula_publicada.turma
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_link(self):
        return bool(self.link_externo) and not self.arquivo

    @property
    def nome_arquivo(self):
        return os.path.basename(self.arquivo.name) if self.arquivo else ''
