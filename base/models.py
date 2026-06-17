from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base inherited by every model in the project.

    Provides automatic creation/update timestamps.
    """

    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        abstract = True
        get_latest_by = 'created_at'
