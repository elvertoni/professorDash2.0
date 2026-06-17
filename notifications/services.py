from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from activities.models import Atividade, Entrega
from classroom.models import AulaPublicada, Matricula

from .models import Notificacao


DUE_SOON_WINDOW = timedelta(hours=24)


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
    matriculas = Matricula.objects.filter(
        turma=turma,
        status=Matricula.Status.ATIVA,
        aluno__is_active=True,
    ).select_related('aluno')
    for matricula in matriculas:
        notify_user(
            matricula.aluno,
            tipo,
            titulo,
            mensagem,
            link=link,
            dedupe_key=dedupe_key,
        )


def notify_aula_publicada(aula_publicada):
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


def notify_atividade_publicada(atividade):
    if not atividade.publicada:
        return

    notify_active_students(
        atividade.turma,
        Notificacao.Tipo.ATIVIDADE,
        'Nova atividade publicada',
        f'{atividade.titulo} está disponível em {atividade.turma.nome}.',
        reverse('activities:aluno_entrega', kwargs={'pk': atividade.pk}),
        f'atividade:{atividade.pk}',
    )


def notify_entrega_corrigida(entrega):
    if not entrega.checked:
        return

    notify_user(
        entrega.aluno,
        Notificacao.Tipo.CORRECAO,
        'Entrega corrigida',
        (
            f'{entrega.atividade.titulo} recebeu nota '
            f'{entrega.nota}/{entrega.atividade.pontuacao_max}.'
        ),
        link=reverse('activities:aluno_entrega', kwargs={'pk': entrega.atividade_id}),
        dedupe_key=f'correcao:{entrega.pk}',
    )


def ensure_timed_notifications_for_user(user):
    if not user.is_authenticated or not user.is_aluno:
        return

    ensure_available_lesson_notifications_for_user(user)
    ensure_due_soon_notifications_for_user(user)


def ensure_available_lesson_notifications_for_user(user):
    publicadas = (
        AulaPublicada.objects.available()
        .filter(
            turma__matriculas__aluno=user,
            turma__matriculas__status=Matricula.Status.ATIVA,
        )
        .select_related('aula', 'turma')
        .distinct()
        .order_by('-disponivel_em')[:20]
    )
    for publicada in publicadas:
        notify_user(
            user,
            Notificacao.Tipo.AULA,
            'Nova aula disponível',
            f'{publicada.aula.titulo} foi liberada em {publicada.turma.nome}.',
            link=reverse('classroom:aluno_aula_detail', kwargs={'pk': publicada.pk}),
            dedupe_key=f'aula:{publicada.pk}',
        )


def ensure_due_soon_notifications_for_user(user):
    now = timezone.now()
    soon = now + DUE_SOON_WINDOW
    delivered_ids = Entrega.objects.filter(
        aluno=user,
        data_entrega__isnull=False,
    ).values_list('atividade_id', flat=True)
    atividades = (
        Atividade.objects.filter(
            publicada=True,
            prazo__gt=now,
            prazo__lte=soon,
            turma__matriculas__aluno=user,
            turma__matriculas__status=Matricula.Status.ATIVA,
        )
        .exclude(id__in=delivered_ids)
        .select_related('turma')
        .distinct()
        .order_by('prazo')
    )
    for atividade in atividades:
        prazo = timezone.localtime(atividade.prazo).strftime('%d/%m/%Y às %H:%M')
        notify_user(
            user,
            Notificacao.Tipo.PRAZO,
            'Prazo próximo',
            f'{atividade.titulo} vence em {prazo}.',
            link=reverse('activities:aluno_entrega', kwargs={'pk': atividade.pk}),
            dedupe_key=f'prazo:{atividade.pk}:{atividade.prazo.isoformat()}',
        )
