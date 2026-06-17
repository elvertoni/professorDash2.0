# AGENTS.md — Prof. Toni Coimbra

> Regras sempre ativas para qualquer agente de IA. Leitura obrigatória antes de codar. Detalhe em `PRD_PROF_DASH.md`; UI em `design_system/design-system.html`; arquitetura detalhada em `CLAUDE.md`.

## Fonte de verdade
- `PRD_PROF_DASH.md` = especificação (domínio, models, RF/RNF, pipeline de import, sprints). Código segue o PRD, nunca o contrário. **Estado das sprints = checklist da seção 9** — confira antes de iniciar qualquer sprint.
- `design_system/design-system.html` = UI obrigatória. NÃO invente componentes fora dele.
- `CLAUDE.md` = arquitetura detalhada (apps, fluxos, convenções) — complementar a este arquivo.
- Antes de cada sprint: releia PRD + design system + código existente.
- Conflito → ordem: **regras invioláveis > design system > PRD > convenção Django**.

## O produto
Portal educacional **single-tenant** (SEED-PR, alunos 14–18). Professor publica aulas por turma, cria atividades, corrige entregas (check+nota+feedback). Aluno acessa aula, estuda, entrega, vê progresso. Consome o acervo PROF-TONI, nunca o reescreve.

## Comandos (Windows / PowerShell)
Ambiente: `.venv` na raiz, Python >3.13, Django 6.0. Use **`uv`** para instalar — a `.venv` não tem `pip`:

```powershell
.\.venv\Scripts\Activate.ps1
uv pip install --python .\.venv\Scripts\python.exe -r requirements.txt
```

Setup inicial: copie `.env.example` → `.env` e preencha `DATABASE_URL` (**PostgreSQL obrigatório** — settings não suporta SQLite).

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver          # validação é MANUAL via runserver + navegador
python manage.py makemigrations <app>
docker compose up -d                # dev: app + Postgres 17 (exige Docker instalado)
```

Management commands custom:
- `base/seed_demo` — dados fake de demonstração (`--password`, `--reset-passwords`).
- `catalog/import_acervo --path ../PROF-TONI [--only-aprovada] [--disciplina <slug>]` — idempotente por `(disciplina,trilha,ordem,slug)`; lê `manifesto.json` + `aulas/**/canonica.md`, converte blocos `:::conceito/:::atencao/:::dica` e diagramas para HTML. Detalhe na seção 6 do PRD.

## NÃO há testes automatizados
Decisão do projeto (PRD proíbe). **NÃO** tente rodar `pytest`, `manage.py test`, ou criar testes. Validação é manual via `runserver` + navegador. Reporte passos de validação manual ao fim da sprint.

## Regras invioláveis
1. Python >3.13 em `.venv` na raiz. `requirements.txt` na raiz, sempre atualizado.
2. Django 6.0. UM `settings.py` (`core/settings.py`). Credenciais em `.env` (gitignored) via django-environ.
3. App de config: `core`. App compartilhado: `base`. Apps de domínio na RAIZ (sem `apps/`, sem `src/`).
4. Auth nativa do Django. **Login por EMAIL**: `AUTH_USER_MODEL = 'accounts.User'`, `USERNAME_FIELD = 'email'`, `User.role` (TextChoices: professor/aluno/admin). Nunca username.
5. Todo model herda `TimeStampedModel` (abstract em `base`): `created_at`, `updated_at`.
6. Código em INGLÊS. UI 100% em PORTUGUÊS BRASILEIRO. Timezone `America/Sao_Paulo`.
7. Aspas simples. PEP8. Class Based Views e recursos nativos do Django sempre que possível.
8. Signals em `signals.py` da app correspondente.
9. **Media protegida**: `PROTECTED_MEDIA_ROOT` (raiz/`protected_media`) é separada de `MEDIA_ROOT` e **não tem URL pública**. Materiais/entregas servidos só por view com checagem de permissão (aluno da turma ou professor). Ver `base/storage.py`.
10. **SINGLE-TENANT**: sem campos/middleware de tenant. Escopo de visibilidade por `Matricula`/turma.

## Apps (todos na raiz, mesmo nível de `manage.py`)
- `core` — config do projeto (único `settings.py`, `urls.py`, view `/health/`).
- `base` — `TimeStampedModel` (abstract, herdado por todos), mixins de permissão, storage protegido, `HomeView`/`health`.
- `accounts` — `User` custom (login por email, `role`), `ProfessorProfile`, `AlunoProfile`, `signals.py`.
- `catalog` — `Disciplina`, `Trilha`, `Aula` (`conteudo_html`/`conteudo_md`); `import_acervo`, `parser.py`.
- `classroom` — `Turma`, `Matricula`, `AulaPublicada` (`disponivel_em`), `ProgressoAula`; `services.py`, `reports.py`.
- `materials` — `Material` (FileField protegido ou link).
- `activities` — `Atividade`, `Entrega`, `EntregaArquivo`; "check" do professor = `nota`+`feedback`+`checked` na `Entrega`.
- `notifications` — `Notificacao` (sino no header); `signals.py`, `context_processors.notification_summary` registrado em `settings.TEMPLATES`.

URLs prefixadas: `/conta/` `/catalogo/` `/turmas/` `/atividades/` `/materiais/` `/notificacoes/` `/health/`.

## Proibido
- Multi-tenant, Celery, RabbitMQ, Redis-broker, Docker Swarm, Traefik.
- LangChain/LangGraph/agentes de IA/OpenAI (fora desta fase).
- Pasta `apps/` ou `src/`. Renomear `core`/`base`. Múltiplos `settings.py`.
- Login por username. Models sem `created_at`/`updated_at`.
- Expor media sem checagem de permissão. Testes automatizados.
- Trocar Django/PostgreSQL. Over-engineering (abstrações sem necessidade).
- Inventar design system fora de `design_system/design-system.html`.

## Fluxo de trabalho
- SPRINT-DRIVEN (seção 9 do PRD). Uma sprint por vez, em ordem. Definition of done = `[x]` no PRD.
- Estado atual documentado: Sprints 0–11 concluídas; resta a Sprint 12 (deploy em produção). Sempre confirme no PRD antes de iniciar.
- Ambiguidade: decida com best practice Django e **documente no PRD** (não em comentário solto).
- Git é do humano. NÃO commit/push a menos que pedido.
- Após sprint: reporte o que foi feito, decisões e como validar manualmente.
