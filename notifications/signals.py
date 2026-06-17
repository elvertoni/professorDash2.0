from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from activities.models import Atividade, Entrega
from classroom.models import AulaPublicada

from .services import (
    notify_atividade_publicada,
    notify_aula_publicada,
    notify_entrega_corrigida,
)


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


@receiver(pre_save, sender=Atividade, dispatch_uid='remember_atividade_state')
def remember_atividade_state(sender, instance, **kwargs):
    if not instance.pk:
        instance._was_publicada = None
        return
    previous = Atividade.objects.filter(pk=instance.pk).values('publicada').first()
    instance._was_publicada = previous['publicada'] if previous else None


@receiver(post_save, sender=Atividade, dispatch_uid='notify_new_atividade')
def notify_new_atividade(sender, instance, created, **kwargs):
    was_publicada = getattr(instance, '_was_publicada', None)
    if instance.publicada and (created or was_publicada is False):
        notify_atividade_publicada(instance)


@receiver(pre_save, sender=Entrega, dispatch_uid='remember_entrega_state')
def remember_entrega_state(sender, instance, **kwargs):
    if not instance.pk:
        instance._was_checked = False
        return
    previous = Entrega.objects.filter(pk=instance.pk).values('checked').first()
    instance._was_checked = previous['checked'] if previous else False


@receiver(post_save, sender=Entrega, dispatch_uid='notify_checked_entrega')
def notify_checked_entrega(sender, instance, **kwargs):
    was_checked = getattr(instance, '_was_checked', False)
    if instance.checked and not was_checked:
        notify_entrega_corrigida(instance)
