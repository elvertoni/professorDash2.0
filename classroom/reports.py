import csv
import io

from django.db.models import Count
from django.utils import timezone

from activities.models import Atividade, AtividadeCheck

from .models import AulaPublicada, Matricula, ProgressoAula

BRAND = '#6d28d9'
INK = '#1f2937'
MUTED = '#6b7280'
LINE = '#e5e7eb'
HEAD_BG = '#f3f0ff'


def _fmt_dt(value):
    if not value:
        return '—'
    return timezone.localtime(value).strftime('%d/%m/%Y %H:%M')


def aluno_check_rows(turma, aluno):
    """Itens de atividade da turma e se o aluno foi marcado como feito."""
    atividades = list(
        Atividade.objects.filter(turma=turma).order_by('-data', 'created_at')
    )
    checks = {
        check.atividade_id: check
        for check in AtividadeCheck.objects.filter(
            atividade__turma=turma, aluno=aluno
        )
    }
    rows = []
    feitos = 0
    for atividade in atividades:
        check = checks.get(atividade.id)
        feito = bool(check and check.feito)
        if feito:
            feitos += 1
        rows.append(
            {
                'atividade': atividade,
                'feito': feito,
                'observacao': check.observacao if check else '',
            }
        )
    return rows, feitos, len(atividades)


def aluno_progress(turma, aluno):
    """(concluídas, total, percentual) de aulas disponíveis da turma."""
    disponiveis = list(
        AulaPublicada.objects.available().filter(turma=turma).values_list('id', flat=True)
    )
    total = len(disponiveis)
    if not total:
        return 0, 0, 0
    concluidas = ProgressoAula.objects.filter(
        aluno=aluno, aula_publicada_id__in=disponiveis, concluido=True
    ).count()
    return concluidas, total, round(concluidas * 100 / total)


def turma_report_rows(turma):
    """Linha por matrícula ativa: progresso de aulas + checks feitos (bulk)."""
    matriculas = list(
        Matricula.objects.filter(turma=turma, status=Matricula.Status.ATIVA)
        .select_related('aluno')
        .order_by('aluno__nome_completo')
    )
    if not matriculas:
        return []

    aluno_ids = [m.aluno_id for m in matriculas]

    disponiveis = list(
        AulaPublicada.objects.available().filter(turma=turma).values_list('id', flat=True)
    )
    total_aulas = len(disponiveis)

    progressos = {}
    if disponiveis and aluno_ids:
        progressos = dict(
            ProgressoAula.objects.filter(
                aluno_id__in=aluno_ids,
                aula_publicada_id__in=disponiveis,
                concluido=True,
            )
            .values('aluno')
            .annotate(c=Count('id'))
            .values_list('aluno', 'c')
        )

    atividade_ids = list(
        Atividade.objects.filter(turma=turma).values_list('id', flat=True)
    )
    total_atividades = len(atividade_ids)

    checks_feitos = {}
    if atividade_ids and aluno_ids:
        checks_feitos = dict(
            AtividadeCheck.objects.filter(
                atividade_id__in=atividade_ids,
                aluno_id__in=aluno_ids,
                feito=True,
            )
            .values('aluno')
            .annotate(c=Count('id'))
            .values_list('aluno', 'c')
        )

    rows = []
    for matricula in matriculas:
        aluno = matricula.aluno
        concluidas = progressos.get(aluno.id, 0)
        pct = round(concluidas * 100 / total_aulas) if total_aulas else 0
        rows.append(
            {
                'aluno': aluno,
                'data_matricula': matricula.data_matricula,
                'concluidas': concluidas,
                'total_aulas': total_aulas,
                'progresso_pct': pct,
                'checks_feitos': checks_feitos.get(aluno.id, 0),
                'total_atividades': total_atividades,
            }
        )
    return rows


# --- Geração de PDF (Reportlab) ---


def _styles():
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

    base = getSampleStyleSheet()
    return {
        'title': ParagraphStyle(
            'pd_title', parent=base['Title'], fontSize=18, textColor=BRAND,
            spaceAfter=2, alignment=TA_LEFT,
        ),
        'subtitle': ParagraphStyle(
            'pd_subtitle', parent=base['Normal'], fontSize=10, textColor=MUTED,
            spaceAfter=12,
        ),
        'h2': ParagraphStyle(
            'pd_h2', parent=base['Heading2'], fontSize=12, textColor=INK,
            spaceBefore=10, spaceAfter=6,
        ),
        'meta': ParagraphStyle(
            'pd_meta', parent=base['Normal'], fontSize=9, textColor=MUTED,
        ),
        'cell': ParagraphStyle(
            'pd_cell', parent=base['Normal'], fontSize=9, textColor=INK,
        ),
    }


def _table_style():
    from reportlab.lib import colors

    return [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(HEAD_BG)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(BRAND)),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor(INK)),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor(LINE)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]


def _document(buffer, title):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate

    return SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=title,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )


def build_boletim_pdf(turma, aluno):
    from reportlab.platypus import Paragraph, Spacer, Table

    styles = _styles()
    rows, feitos, total_atividades = aluno_check_rows(turma, aluno)
    concluidas, total_aulas, progresso_pct = aluno_progress(turma, aluno)

    buffer = io.BytesIO()
    doc = _document(buffer, f'Boletim · {aluno.nome_completo}')
    story = [
        Paragraph('Prof. Toni Coimbra · Boletim do aluno', styles['title']),
        Paragraph(
            f'{aluno.nome_completo} — {turma.nome} · {turma.disciplina.label} · '
            f'{turma.serie} · {turma.ano_letivo}',
            styles['subtitle'],
        ),
        Paragraph(
            f'Progresso de aulas: <b>{progresso_pct}%</b> '
            f'({concluidas}/{total_aulas}) &nbsp;·&nbsp; '
            f'Atividades feitas: <b>{feitos}/{total_atividades}</b>',
            styles['meta'],
        ),
        Spacer(1, 12),
        Paragraph('Atividades (controle do professor)', styles['h2']),
    ]

    data = [['Atividade', 'Data', 'Feito', 'Observação']]
    for row in rows:
        atividade = row['atividade']
        data.append(
            [
                Paragraph(atividade.titulo, styles['cell']),
                atividade.data.strftime('%d/%m/%Y') if atividade.data else '—',
                'Sim' if row['feito'] else 'Não',
                Paragraph(row['observacao'] or '—', styles['cell']),
            ]
        )
    if len(data) == 1:
        data.append([Paragraph('Nenhuma atividade cadastrada.', styles['cell']), '', '', ''])

    table = Table(data, colWidths=[185, 75, 50, 130], repeatRows=1)
    table.setStyle(_table_style())
    story.append(table)
    story.append(Spacer(1, 16))
    story.append(
        Paragraph(
            f'Emitido em {_fmt_dt(timezone.now())} · Prof. Toni Coimbra · Boletim',
            styles['meta'],
        )
    )

    doc.build(story)
    return buffer.getvalue()


def build_turma_report_pdf(turma):
    from reportlab.platypus import Paragraph, Spacer, Table

    styles = _styles()
    rows = turma_report_rows(turma)

    buffer = io.BytesIO()
    doc = _document(buffer, f'Relatório · {turma.nome}')
    story = [
        Paragraph('Prof. Toni Coimbra · Relatório de turma', styles['title']),
        Paragraph(
            f'{turma.nome} · {turma.disciplina.label} · {turma.serie} · '
            f'{turma.ano_letivo} · Prof. {turma.professor.get_short_name}',
            styles['subtitle'],
        ),
        Paragraph(
            f'Alunos ativos: <b>{len(rows)}</b>',
            styles['meta'],
        ),
        Spacer(1, 12),
        Paragraph('Progresso por aluno', styles['h2']),
    ]

    data = [['Aluno', 'Matrícula', 'Aulas concluídas', 'Progresso', 'Atividades feitas']]
    for row in rows:
        data.append(
            [
                Paragraph(row['aluno'].nome_completo, styles['cell']),
                row['data_matricula'].strftime('%d/%m/%Y'),
                f'{row["concluidas"]}/{row["total_aulas"]}',
                f'{row["progresso_pct"]}%',
                f'{row["checks_feitos"]}/{row["total_atividades"]}',
            ]
        )
    if len(rows) == 0:
        data.append([Paragraph('Nenhuma matrícula ativa.', styles['cell']), '', '', '', ''])

    table = Table(data, colWidths=[170, 70, 95, 65, 90], repeatRows=1)
    table.setStyle(_table_style())
    story.append(table)
    story.append(Spacer(1, 16))
    story.append(
        Paragraph(
            f'Emitido em {_fmt_dt(timezone.now())} · Prof. Toni Coimbra · Relatório',
            styles['meta'],
        )
    )

    doc.build(story)
    return buffer.getvalue()


def build_turma_report_csv(turma):
    rows = turma_report_rows(turma)
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=';')
    writer.writerow(
        [
            'Aluno', 'Email', 'Data da matricula', 'Aulas concluidas',
            'Total de aulas', 'Progresso (%)', 'Atividades feitas', 'Total atividades',
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row['aluno'].nome_completo,
                row['aluno'].email,
                row['data_matricula'].strftime('%d/%m/%Y'),
                row['concluidas'],
                row['total_aulas'],
                row['progresso_pct'],
                row['checks_feitos'],
                row['total_atividades'],
            ]
        )
    return buffer.getvalue()
