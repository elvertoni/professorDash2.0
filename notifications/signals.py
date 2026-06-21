from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from classroom.models import AulaPublicada

from .services import notify_aula_publicada


@receiver(pre_save, sender=AulaPublicada, dispatch_uid='remember_aula_publicada_state')
def remember_aula_publicada_state(sender, instance, **kwargs):
    if not instance.pk:
        instance._was_publicada = None
        return
    previous = AulaPublicada.objects.filter(pk=instance.pk).values('publicada').first()
    instance._was_publicada = previous['publicada'] if previous else None


@receiver(post_save, sender=AulaPublicada, dispatch_uid='notify_new_aula_publicada')
def notify_new_aula_publicada(sender, instance, created, **kwargs):
    was_publicada = getattr(instance, '_was_publicada', None)
    if instance.publicada and (created or was_publicada is False):
        notify_aula_publicada(instance)
