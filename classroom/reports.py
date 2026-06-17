import csv
import io

from django.utils import timezone

from activities.models import Atividade, Entrega

from .models import AulaPublicada, Matricula, ProgressoAula

BRAND = '#6d28d9'
INK = '#1f2937'
MUTED = '#6b7280'
LINE = '#e5e7eb'
HEAD_BG = '#f3f0ff'


def _fmt_nota(nota):
    if nota is None:
        return '—'
    return f'{nota:.1f}'.replace('.', ',')


def _fmt_dt(value):
    if not value:
        return '—'
    return timezone.localtime(value).strftime('%d/%m/%Y %H:%M')


def aluno_grade_rows(turma, aluno):
    """Notas do aluno por atividade publicada da turma, com média simples."""
    atividades = list(
        Atividade.objects.filter(turma=turma, publicada=True).order_by(
            'prazo', 'created_at'
        )
    )
    entregas = {
        entrega.atividade_id: entrega
        for entrega in Entrega.objects.filter(
            atividade__turma=turma, aluno=aluno
        ).select_related('atividade')
    }
    rows = []
    notas = []
    for atividade in atividades:
        entrega = entregas.get(atividade.id)
        nota = entrega.nota if entrega and entrega.checked else None
        if nota is not None:
            notas.append(float(nota))
        rows.append(
            {
                'atividade': atividade,
                'entrega': entrega,
                'nota': nota,
                'status': entrega.get_status_display() if entrega else 'Pendente',
            }
        )
    media = round(sum(notas) / len(notas), 1) if notas else None
    return rows, media


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
    """Linha por matrícula ativa com progresso e média de notas."""
    matriculas = (
        Matricula.objects.filter(turma=turma, status=Matricula.Status.ATIVA)
        .select_related('aluno')
        .order_by('aluno__nome_completo')
    )
    rows = []
    for matricula in matriculas:
        aluno = matricula.aluno
        _, media = aluno_grade_rows(turma, aluno)
        concluidas, total, pct = aluno_progress(turma, aluno)
        rows.append(
            {
                'aluno': aluno,
                'data_matricula': matricula.data_matricula,
                'media': media,
                'concluidas': concluidas,
                'total_aulas': total,
                'progresso_pct': pct,
            }
        )
    return rows


# --- Geração de PDF (Reportlab) ---


def _styles():
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

    base = getSampleStyleSheet()
    styles = {
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
    return styles


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
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph, Spacer, Table

    styles = _styles()
    rows, media = aluno_grade_rows(turma, aluno)
    concluidas, total_aulas, progresso_pct = aluno_progress(turma, aluno)

    buffer = io.BytesIO()
    doc = _document(buffer, f'Boletim · {aluno.nome_completo}')
    story = [
        Paragraph('ProfessorDash · Boletim do aluno', styles['title']),
        Paragraph(
            f'{aluno.nome_completo} — {turma.nome} · {turma.disciplina.label} · '
            f'{turma.serie} · {turma.ano_letivo}',
            styles['subtitle'],
        ),
        Paragraph(
            f'Média geral: <b>{_fmt_nota(media)}</b> &nbsp;·&nbsp; '
            f'Progresso de aulas: <b>{progresso_pct}%</b> '
            f'({concluidas}/{total_aulas})',
            styles['meta'],
        ),
        Spacer(1, 12),
        Paragraph('Notas por atividade', styles['h2']),
    ]

    data = [['Atividade', 'Prazo', 'Status', 'Nota', 'Máx.']]
    for row in rows:
        atividade = row['atividade']
        data.append(
            [
                Paragraph(atividade.titulo, styles['cell']),
                _fmt_dt(atividade.prazo),
                row['status'],
                _fmt_nota(row['nota']),
                _fmt_nota(atividade.pontuacao_max),
            ]
        )
    if len(data) == 1:
        data.append([Paragraph('Nenhuma atividade publicada.', styles['cell']), '', '', '', ''])

    table = Table(data, colWidths=[210, 95, 75, 45, 45], repeatRows=1)
    table.setStyle(_table_style())
    story.append(table)
    story.append(Spacer(1, 16))
    story.append(
        Paragraph(
            f'Emitido em {_fmt_dt(timezone.now())} · ProfessorDash',
            styles['meta'],
        )
    )

    doc.build(story)
    return buffer.getvalue()


def build_turma_report_pdf(turma):
    from reportlab.platypus import Paragraph, Spacer, Table

    styles = _styles()
    rows = turma_report_rows(turma)
    medias = [row['media'] for row in rows if row['media'] is not None]
    media_turma = round(sum(medias) / len(medias), 1) if medias else None

    buffer = io.BytesIO()
    doc = _document(buffer, f'Relatório · {turma.nome}')
    story = [
        Paragraph('ProfessorDash · Relatório de turma', styles['title']),
        Paragraph(
            f'{turma.nome} · {turma.disciplina.label} · {turma.serie} · '
            f'{turma.ano_letivo} · Prof. {turma.professor.get_short_name}',
            styles['subtitle'],
        ),
        Paragraph(
            f'Alunos ativos: <b>{len(rows)}</b> &nbsp;·&nbsp; '
            f'Média da turma: <b>{_fmt_nota(media_turma)}</b>',
            styles['meta'],
        ),
        Spacer(1, 12),
        Paragraph('Desempenho por aluno', styles['h2']),
    ]

    data = [['Aluno', 'Matrícula', 'Aulas concluídas', 'Progresso', 'Média']]
    for row in rows:
        data.append(
            [
                Paragraph(row['aluno'].nome_completo, styles['cell']),
                row['data_matricula'].strftime('%d/%m/%Y'),
                f'{row["concluidas"]}/{row["total_aulas"]}',
                f'{row["progresso_pct"]}%',
                _fmt_nota(row['media']),
            ]
        )
    if len(rows) == 0:
        data.append([Paragraph('Nenhuma matrícula ativa.', styles['cell']), '', '', '', ''])

    table = Table(data, colWidths=[180, 75, 95, 70, 50], repeatRows=1)
    table.setStyle(_table_style())
    story.append(table)
    story.append(Spacer(1, 16))
    story.append(
        Paragraph(
            f'Emitido em {_fmt_dt(timezone.now())} · ProfessorDash',
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
        ['Aluno', 'Email', 'Data da matricula', 'Aulas concluidas', 'Total de aulas', 'Progresso (%)', 'Media']
    )
    for row in rows:
        media = '' if row['media'] is None else f'{row["media"]:.1f}'.replace('.', ',')
        writer.writerow(
            [
                row['aluno'].nome_completo,
                row['aluno'].email,
                row['data_matricula'].strftime('%d/%m/%Y'),
                row['concluidas'],
                row['total_aulas'],
                row['progresso_pct'],
                media,
            ]
        )
    return buffer.getvalue()
