import secrets
import string

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from base.models import TimeStampedModel
from catalog.models import Aula, Disciplina


INVITE_CODE_ALPHABET = string.ascii_uppercase + string.digits


def generate_invite_code(length=8):
    return ''.join(secrets.choice(INVITE_CODE_ALPHABET) for _ in range(length))


class Turma(TimeStampedModel):
    nome = models.CharField('nome', max_length=180)
    disciplina = models.ForeignKey(
        Disciplina,
        verbose_name='disciplina',
        on_delete=models.PROTECT,
        related_name='turmas',
    )
    serie = models.CharField('série', max_length=80)
    ano_letivo = models.PositiveSmallIntegerField('ano letivo')
    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='professor',
        on_delete=models.PROTECT,
        related_name='turmas_lecionadas',
        limit_choices_to={'role': 'professor'},
    )
    codigo_convite = models.CharField(
        'código de convite',
        max_length=12,
        unique=True,
        blank=True,
        editable=False,
    )
    ativa = models.BooleanField('ativa', default=True)

    class Meta:
        verbose_name = 'turma'
        verbose_name_plural = 'turmas'
        ordering = ['-ano_letivo', 'nome']
        indexes = [
            models.Index(fields=['professor', 'ativa']),
            models.Index(fields=['codigo_convite']),
        ]

    def __str__(self):
        return f'{self.nome} · {self.ano_letivo}'

    def save(self, *args, **kwargs):
        if not self.codigo_convite:
            self.codigo_convite = self.make_unique_invite_code()
        super().save(*args, **kwargs)

    def make_unique_invite_code(self):
        code = generate_invite_code()
        while Turma.objects.filter(codigo_convite=code).exists():
            code = generate_invite_code()
        return code

    def regenerate_invite_code(self):
        self.codigo_convite = self.make_unique_invite_code()
        self.save(update_fields=['codigo_convite', 'updated_at'])

    def get_absolute_url(self):
        return reverse('classroom:turma_detail', kwargs={'pk': self.pk})

    @property
    def active_students_count(self):
        return self.matriculas.filter(status=Matricula.Status.ATIVA).count()


class Matricula(TimeStampedModel):
    class Status(models.TextChoices):
        ATIVA = 'ativa', 'Ativa'
        INATIVA = 'inativa', 'Inativa'

    turma = models.ForeignKey(
        Turma,
        verbose_name='turma',
        on_delete=models.CASCADE,
        related_name='matriculas',
    )
    aluno = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='aluno',
        on_delete=models.PROTECT,
        related_name='matriculas',
        limit_choices_to={'role': 'aluno'},
    )
    data_matricula = models.DateField(
        'data da matrícula',
        default=timezone.localdate,
    )
    status = models.CharField(
        'status',
        max_length=20,
        choices=Status.choices,
        default=Status.ATIVA,
    )

    class Meta:
        verbose_name = 'matrícula'
        verbose_name_plural = 'matrículas'
        ordering = ['turma__nome', 'aluno__nome_completo']
        constraints = [
            models.UniqueConstraint(
                fields=['turma', 'aluno'],
                name='unique_matricula_por_turma_aluno',
            ),
        ]
        indexes = [
            models.Index(fields=['turma', 'status']),
            models.Index(fields=['aluno', 'status']),
        ]

    def __str__(self):
        return f'{self.aluno} em {self.turma}'

    def deactivate(self):
        self.status = self.Status.INATIVA
        self.save(update_fields=['status', 'updated_at'])


class AulaPublicadaQuerySet(models.QuerySet):
    def published(self):
        return self.filter(publicada=True)

    def available(self, now=None):
        now = now or timezone.now()
        return self.published().filter(disponivel_em__lte=now)


class AulaPublicada(TimeStampedModel):
    turma = models.ForeignKey(
        Turma,
        verbose_name='turma',
        on_delete=models.CASCADE,
        related_name='aulas_publicadas',
    )
    aula = models.ForeignKey(
        Aula,
        verbose_name='aula',
        on_delete=models.PROTECT,
        related_name='publicacoes',
    )
    ordem_na_turma = models.PositiveIntegerField('ordem na turma', default=0)
    disponivel_em = models.DateTimeField(
        'disponível em',
        default=timezone.now,
        help_text='Data e hora de liberação da aula para a turma.',
    )
    publicada = models.BooleanField('publicada', default=True)

    objects = AulaPublicadaQuerySet.as_manager()

    class Meta:
        verbose_name = 'aula publicada'
        verbose_name_plural = 'aulas publicadas'
        ordering = ['turma', 'ordem_na_turma', 'aula__ordem']
        constraints = [
            models.UniqueConstraint(
                fields=['turma', 'aula'],
                name='unique_aula_publicada_por_turma',
            ),
        ]
        indexes = [
            models.Index(fields=['turma', 'publicada', 'disponivel_em']),
        ]

    def __str__(self):
        return f'{self.aula.titulo} → {self.turma.nome}'

    @property
    def is_available(self):
        return self.publicada and self.disponivel_em <= timezone.now()

    @property
    def is_scheduled(self):
        return self.publicada and self.disponivel_em > timezone.now()


class ProgressoAula(TimeStampedModel):
    aluno = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='aluno',
        on_delete=models.CASCADE,
        related_name='progressos',
        limit_choices_to={'role': 'aluno'},
    )
    aula_publicada = models.ForeignKey(
        AulaPublicada,
        verbose_name='aula publicada',
        on_delete=models.CASCADE,
        related_name='progressos',
    )
    visto_em = models.DateTimeField('visto em', default=timezone.now)
    concluido = models.BooleanField('concluído', default=False)
    concluido_em = models.DateTimeField('concluído em', blank=True, null=True)

    class Meta:
        verbose_name = 'progresso de aula'
        verbose_name_plural = 'progressos de aulas'
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['aluno', 'aula_publicada'],
                name='unique_progresso_por_aluno_aula',
            ),
        ]
        indexes = [
            models.Index(fields=['aluno', 'concluido']),
        ]

    def __str__(self):
        return f'{self.aluno} · {self.aula_publicada}'

    def mark_done(self):
        self.concluido = True
        self.concluido_em = timezone.now()
        self.save(update_fields=['concluido', 'concluido_em', 'updated_at'])

    def mark_undone(self):
        self.concluido = False
        self.concluido_em = None
        self.save(update_fields=['concluido', 'concluido_em', 'updated_at'])
