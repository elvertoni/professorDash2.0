# AGENTS.md — ProfessorDash

> Regras sempre ativas para qualquer agente de IA trabalhando neste projeto. Leitura obrigatória antes de codar. Detalhe completo em `PRD_PROF_DASH.md`. UI em `design_system/design-system.html`.

## Fonte de verdade
- `PRD_PROF_DASH.md` = especificação (domínio, models, RF/RNF, pipeline de import, sprints). O código segue o PRD, nunca o contrário.
- `design_system/design-system.html` = fonte obrigatória de UI. NÃO invente componentes fora dele.
- Antes de cada sprint: releia PRD + design system + código existente.

## O produto
Portal educacional (SEED-PR, alunos 14–18). Professor publica aulas por turma, cria atividades, corrige entregas (check+nota+feedback). Aluno acessa aula, estuda, entrega, vê progresso. Ponte entre o acervo de aulas e o aluno.

## Regras invioláveis
1. Python >3.13 em `.venv` na raiz. `requirements.txt` na raiz, sempre atualizado.
2. Django >6.0. UM `settings.py`. Credenciais em `.env` (gitignored) via django-environ.
3. App de config: `core`. App compartilhado: `base`. Apps de domínio na RAIZ (sem `apps/`, sem `src/`).
4. Auth nativa do Django. LOGIN POR EMAIL (não username).
5. Todo model herda `TimeStampedModel` (abstract em `base`): `created_at`, `updated_at`.
6. Código em INGLÊS. UI 100% em PORTUGUÊS BRASILEIRO. Timezone `America/Sao_Paulo`.
7. Aspas simples. PEP8. Class Based Views e recursos nativos do Django sempre que possível.
8. Signals em `signals.py` da app correspondente.
9. Media protegida: materiais/entregas servidos só a usuário autorizado (aluno da turma ou professor). Nunca expor publicamente.
10. SINGLE-TENANT: sem campos/middleware de tenant. Escopo de visibilidade por matrícula/turma.

## Proibido
- Multi-tenant, Celery, RabbitMQ, Redis-broker, Docker Swarm, Traefik.
- LangChain/LangGraph/agentes de IA/OpenAI (fora desta fase).
- Pasta `apps/` ou `src/`. Renomear `core`/`base`. Múltiplos `settings.py`.
- Login por username. Models sem `created_at`/`updated_at`.
- Expor media sem checagem de permissão. Testes automatizados.
- Trocar Django/PostgreSQL. Over-engineering (abstrações sem necessidade).
- Inventar design system fora de `design_system/design-system.html`.

## Stack
Django >6.0 / Python >3.13 · PostgreSQL · Django Templates + HTMX + Alpine.js + Tailwind/CSS do DS · WhiteNoise · Reportlab+PyPDF · MkDocs+mermaid · Docker Compose + Caddy.

Apps: `core base accounts catalog classroom materials activities notifications`.

## Pipeline do acervo
Command `import_acervo --path <repo PROF-TONI> [--only-aprovada]`: lê `manifesto.json` + `aulas/**/canonica.md`, parseia frontmatter YAML, converte blocos `:::conceito/:::atencao/:::dica` e diagramas para HTML. Idempotente por `(disciplina,trilha,ordem,slug)`. Detalhe na seção 6 do PRD.

## Fluxo de trabalho
- SPRINT-DRIVEN (seção 9 do PRD). Uma sprint por vez, em ordem. Definition of done = `[x]` no PRD.
- Ambiguidade: decida com best practice Django e DOCUMENTE no PRD (não em comentário solto).
- Git é do humano. NÃO faça commit/push a menos que pedido.
- Após sprint: reporte o que foi feito, decisões e como validar manualmente.
- Conflito → ordem: regras invioláveis > design system > PRD > convenção Django.
