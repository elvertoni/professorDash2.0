from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from base.models import TimeStampedModel


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('O e-mail é obrigatório.')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', User.Role.ADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superusuário precisa ter is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superusuário precisa ter is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser, TimeStampedModel):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        PROFESSOR = 'professor', 'Professor'
        ALUNO = 'aluno', 'Aluno'

    username = None
    first_name = None
    last_name = None

    email = models.EmailField('e-mail', unique=True)
    nome_completo = models.CharField('nome completo', max_length=255)
    avatar = models.FileField('avatar', upload_to='avatars/', blank=True)
    role = models.CharField('perfil', max_length=20, choices=Role.choices, default=Role.ALUNO)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome_completo']

    class Meta:
        verbose_name = 'usuário'
        verbose_name_plural = 'usuários'
        ordering = ['email']

    def __str__(self):
        return self.nome_completo or self.email

    def get_full_name(self):
        return self.nome_completo

    def get_short_name(self):
        return self.nome_completo.split()[0] if self.nome_completo else self.email

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    @property
    def is_professor(self):
        return self.role == self.Role.PROFESSOR

    @property
    def is_aluno(self):
        return self.role == self.Role.ALUNO

    @property
    def first_active_turma(self):
        if self.is_aluno:
            matricula = self.matriculas.filter(status='ativa').first()
            return matricula.turma if matricula else None
        elif self.is_professor:
            return self.turmas_lecionadas.filter(ativa=True).first()
        return None


class ProfessorProfile(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name='usuário',
        on_delete=models.CASCADE,
        related_name='professor_profile',
    )
    seed_registration = models.CharField('vínculo SEED', max_length=80, blank=True)
    disciplines = models.TextField('disciplinas que leciona', blank=True)

    class Meta:
        verbose_name = 'perfil de professor'
        verbose_name_plural = 'perfis de professores'
        ordering = ['user__nome_completo']

    def __str__(self):
        return f'Perfil de professor: {self.user}'


class AlunoProfile(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name='usuário',
        on_delete=models.CASCADE,
        related_name='aluno_profile',
    )
    school_registration = models.CharField(
        'matrícula escolar',
        max_length=80,
        blank=True,
        null=True,
        unique=True,
    )
    grade = models.CharField('série', max_length=80, blank=True)
    responsible_name = models.CharField('responsável', max_length=255, blank=True)
    birth_date = models.DateField('data de nascimento', blank=True, null=True)

    class Meta:
        verbose_name = 'perfil de aluno'
        verbose_name_plural = 'perfis de alunos'
        ordering = ['user__nome_completo']

    def __str__(self):
        return f'Perfil de aluno: {self.user}'
