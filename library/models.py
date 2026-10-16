from django.conf import settings
from django.db import models
from django.urls import reverse

from base.models import TimeStampedModel


class Source(TimeStampedModel):
    key = models.SlugField(unique=True)
    label = models.CharField(max_length=120)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    revision = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return self.label


class Note(TimeStampedModel):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='notes')
    path = models.CharField(max_length=500)
    slug = models.CharField(max_length=180)
    title = models.CharField(max_length=300)
    aliases = models.JSONField(default=list, blank=True)
    topic = models.CharField(max_length=180)
    status = models.CharField(max_length=40)
    collections = models.JSONField(default=list, blank=True)
    body = models.TextField()
    references = models.JSONField(default=list, blank=True)
    source_updated = models.CharField(max_length=80, blank=True)
    digest = models.CharField(max_length=64)
    search_title = models.TextField()
    search_text = models.TextField()

    class Meta:
        ordering = ['title', 'pk']
        constraints = [
            models.UniqueConstraint(
                fields=['source', 'path'],
                name='unique_library_source_path',
            )
        ]

    def get_absolute_url(self):
        return reverse('library:detail', kwargs={'pk': self.pk})
