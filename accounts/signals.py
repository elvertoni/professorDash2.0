from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import AlunoProfile, ProfessorProfile, User


@receiver(post_save, sender=User)
def ensure_role_profile(sender, instance, **kwargs):
    if instance.role == User.Role.PROFESSOR:
        ProfessorProfile.objects.get_or_create(user=instance)
    elif instance.role == User.Role.ALUNO:
        AlunoProfile.objects.get_or_create(user=instance)
