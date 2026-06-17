from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import EntregaArquivo


@receiver(post_delete, sender=EntregaArquivo, dispatch_uid='entrega_arquivo_delete_file')
def delete_entrega_arquivo_file(sender, instance, **kwargs):
    if instance.arquivo:
        instance.arquivo.delete(save=False)
