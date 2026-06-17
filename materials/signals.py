from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Material


@receiver(post_delete, sender=Material, dispatch_uid='material_delete_file')
def delete_material_file(sender, instance, **kwargs):
    if instance.arquivo:
        instance.arquivo.delete(save=False)
