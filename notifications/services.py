from django.urls import reverse
from django.utils import timezone

from classroom.models import AulaPublicada, Matricula

from .models import Notificacao


def _sync_deduped_notifications(payloads):
    payloads_by_key = {
        (payload['usuario_id'], payload['tipo'], payload['dedupe_key']): payload
        for payload in payloads
    }
    if not payloads_by_key:
        return

    existing = Notificacao.objects.filter(
        usuario_id__in={key[0] for key in payloads_by_key},
        tipo__in={key[1] for key in payloads_by_key},
        dedupe_key__in={key[2] for key in payloads_by_key},
    ).only(
        'pk',
        'usuario_id',
        'tipo',
        'dedupe_key',
        'titulo',
        'mensagem',
        'link',
    )
    existing_by_key = {
        (item.usuario_id, item.tipo, item.dedupe_key): item
        for item in existing
    }
    now = timezone.now()
    to_create = []
    to_update = []

    for key, payload in payloads_by_key.items():
        notificacao = existing_by_key.get(key)
        if notificacao is None:
            to_create.append(Notificacao(**payload))
            continue

        changed = False
        for field in ('titulo', 'mensagem', 'link'):
            value = payload[field]
            if getattr(notificacao, field) != value:
                setattr(notificacao, field, value)
                changed = True
        if changed:
            notificacao.updated_at = now
            to_update.append(notificacao)

    if to_create:
        Notificacao.objects.bulk_create(to_create, ignore_conflicts=True)
    if to_update:
        Notificacao.objects.bulk_update(
            to_update,
            ['titulo', 'mensagem', 'link', 'updated_at'],
        )


def notify_user(usuario, tipo, titulo, mensagem, link='', dedupe_key=''):
    defaults = {
        'titulo': titulo,
        'mensagem': mensagem,
        'link': link,
    }
    if dedupe_key:
        notificacao, created = Notificacao.objects.get_or_create(
            usuario=usuario,
            tipo=tipo,
            dedupe_key=dedupe_key,
            defaults=defaults,
        )
        if not created:
            changed = []
            for field, value in defaults.items():
                if getattr(notificacao, field) != value:
                    setattr(notificacao, field, value)
                    changed.append(field)
            if changed:
                notificacao.save(update_fields=[*changed, 'updated_at'])
        return notificacao

    return Notificacao.objects.create(
        usuario=usuario,
        tipo=tipo,
        titulo=titulo,
        mensagem=mensagem,
        link=link,
    )


def notify_active_students(turma, tipo, titulo, mensagem, link, dedupe_key):
    aluno_ids = Matricula.objects.filter(
        turma=turma,
        status=Matricula.Status.ATIVA,
        aluno__is_active=True,
    ).values_list('aluno_id', flat=True)
    _sync_deduped_notifications(
        {
            'usuario_id': aluno_id,
            'tipo': tipo,
            'titulo': titulo,
            'mensagem': mensagem,
            'link': link,
            'dedupe_key': dedupe_key,
        }
        for aluno_id in aluno_ids
    )


def notify_aula_publicada(aula_publicada):
    related_cache = aula_publicada._state.fields_cache
    if 'aula' not in related_cache or 'turma' not in related_cache:
        aula_publicada = AulaPublicada.objects.select_related(
            'aula', 'turma'
        ).get(pk=aula_publicada.pk)

    if not aula_publicada.is_available:
        return

    notify_active_students(
        aula_publicada.turma,
        Notificacao.Tipo.AULA,
        'Nova aula disponível',
        (
            f'{aula_publicada.aula.titulo} foi liberada em '
            f'{aula_publicada.turma.nome}.'
        ),
        reverse('classroom:aluno_aula_detail', kwargs={'pk': aula_publicada.pk}),
        f'aula:{aula_publicada.pk}',
    )


def ensure_timed_notifications_for_user(user):
    if not user.is_authenticated or not user.is_aluno:
        return

    ensure_available_lesson_notifications_for_user(user)


def ensure_available_lesson_notifications_for_user(user):
    publicadas = (
        AulaPublicada.objects.available()
        .filter(
            turma__matriculas__aluno=user,
            turma__matriculas__status=Matricula.Status.ATIVA,
        )
        .select_related('aula', 'turma')
        .only('pk', 'aula__titulo', 'turma__nome')
        .distinct()
        .order_by('-disponivel_em')[:20]
    )
    _sync_deduped_notifications(
        {
            'usuario_id': user.pk,
            'tipo': Notificacao.Tipo.AULA,
            'titulo': 'Nova aula disponível',
            'mensagem': (
                f'{publicada.aula.titulo} foi liberada em '
                f'{publicada.turma.nome}.'
            ),
            'link': reverse(
                'classroom:aluno_aula_detail', kwargs={'pk': publicada.pk}
            ),
            'dedupe_key': f'aula:{publicada.pk}',
        }
        for publicada in publicadas
    )
