# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Regras do projeto (ler antes de codar)

As regras **invioláveis** estão em **[AGENTS.md](AGENTS.md)** — leitura obrigatória antes de qualquer tarefa. Fontes de verdade:

- `PRD_PROF_DASH.md` — especificação completa (domínio, models, RF/RNF, pipeline de import, deploy, roadmap de sprints §9).
- `design_system/design-system.html` — UI **obrigatória**. Não inventar componentes fora dele.
- `PROMPT_BUILD_PROF_DASH.md` — prompt de build XML que rege o processo.

Antes de cada sprint: releia PRD + design system + código existente. Ordem em conflito: **regras invioláveis (AGENTS.md) > design system > PRD > convenção Django**.

## Estado atual

O status oficial fica no checklist da seção 9 do `PRD_PROF_DASH.md`; confira o PRD antes de iniciar qualquer sprint. No estado documentado mais recente, as Sprints 0-11 estão marcadas como concluídas. Resta apenas a Sprint 12 (deploy em produção). A Sprint 11 foi executada fora de ordem por override explícito do usuário; as Sprints 9 e 10 foram concluídas em seguida.

Apps implementados no código atualmente: `core`, `base`, `accounts`, `catalog`, `classroom`, `activities`, `materials` e `notifications`. Falta apenas o deploy de produção (artefatos da Sprint 12).

A execução do `docker compose` depende de Docker instalado na máquina.

## Fluxo de trabalho (crítico)

- **Sprint-driven**: uma sprint por vez, em ordem (Sprint 0 → 12, §9 do PRD). Implemente *todas* as tarefas da sprint antes de fechá-la.
- **Definition of done** = marcar `[x]` no checklist do PRD ao concluir cada tarefa.
- **Git é do humano**: NÃO commitar/push a menos que pedido.
- Ambiguidade: decida com best practice Django e **documente no PRD** (não em comentário solto).
- Ao fim da sprint: reporte o que foi feito, decisões e como validar manualmente.
- **Sem testes automatizados** (decisão do projeto — validação é manual via `runserver`).

## Comandos

Ambiente: `.venv` na raiz, Python >3.13, Django >6.0. Ativar no Windows/PowerShell:

Use `uv` para instalar dependências neste ambiente; não assuma que a `.venv` tem `pip` instalado.

```powershell
.\.venv\Scripts\Activate.ps1
uv pip install --python .\.venv\Scripts\python.exe -r requirements.txt
```

Desenvolvimento (após scaffold):

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver          # valida a jornada da sprint manualmente
python manage.py makemigrations <app>
```

Pipeline do acervo (diferencial do produto — §6 do PRD):

```powershell
# Idempotente: casa por (disciplina, trilha, ordem, slug); só atualiza se versao/atualizado_em mudou
python manage.py import_acervo --path ../PROF-TONI --only-aprovada [--disciplina <slug>]
```

> Management commands custom existentes: `catalog/import_acervo` e `base/seed_demo`. A documentação MkDocs existe; os artefatos finais de produção (`docker-compose.prod.yml`, entrypoint, Caddyfile e backup) continuam abertos na Sprint 12.

Docker (dev existe; prod é futuro):

```powershell
docker compose up -d   # dev: app + Postgres (docker-compose.yml na raiz)
```

## Arquitetura

Portal educacional **single-tenant** (Prof. Toni / SEED-PR). É a camada de **entrega ao aluno** de um pipeline de conhecimento: `canonica.md` (acervo PROF-TONI) → import → catálogo → publicação por turma → aluno. O ProfessorDash **consome** o acervo, nunca o reescreve.

**Apps** (todos na raiz, mesmo nível de `manage.py` — proibido `apps/` ou `src/`):

| App | Responsabilidade | Models-chave |
|---|---|---|
| `core` | Config do projeto (único `settings.py`, urls, `/health/`) | — |
| `base` | Recursos compartilhados | `TimeStampedModel` (abstract, herdado por *todos* os models), mixins de permissão, storage protegido de media |
| `accounts` | Usuários e auth | `User` (custom, `email` = `USERNAME_FIELD`, `role` professor/aluno/admin), `ProfessorProfile`, `AlunoProfile` |
| `catalog` | Taxonomia do acervo (espelha `manifesto.json`) | `Disciplina`, `Trilha`, `Aula` (canônica importada: `conteudo_html`/`conteudo_md`) |
| `classroom` | Turmas e publicação | `Turma`, `Matricula`, `AulaPublicada` (Aula→Turma com `disponivel_em`), `ProgressoAula` |
| `materials` | Materiais extras (upload manual) | `Material` (FileField protegido ou link) |
| `activities` | Atividades e correção | `Atividade`, `Entrega`, `EntregaArquivo`; o "check" do professor = `nota`+`feedback`+`checked` na `Entrega` |
| `notifications` | Avisos in-app (sino no header) — planejado na Sprint 9 | `Notificacao` |

**Fluxos centrais:**

- **Acervo → aluno**: `import_acervo` lê `manifesto.json` + `aulas/{disciplina}/{trilha}/{NN-slug}/canonica.md` (frontmatter YAML + corpo Markdown com blocos custom `:::conceito`/`:::atencao`/`:::dica` e fences de diagrama) → parser custom converte para `conteudo_html` fiel ao design system → vira `Aula` no catálogo. Professor publica via `AulaPublicada` (define `disponivel_em` e ordem na turma) → aluno vê respeitando data de liberação.
- **Atividade → check**: professor cria `Atividade` na turma → aluno faz `Entrega` (texto + `EntregaArquivo`, respeita prazo/atraso) → professor dá "check" (nota + feedback). Disparo de `Notificacao` pertence à Sprint 9.
- **Escopo de visibilidade** (em vez de tenant): aluno só enxerga turmas/aulas/atividades das suas `Matricula`. Toda rota privada exige auth + papel.
- **Media protegida**: materiais e entregas NUNCA expostos publicamente — servidos via view com checagem de permissão (aluno da turma ou professor).

## Convenções de código

- Código em **inglês** (nomes, classes, variáveis). UI **100% pt-BR**. Timezone `America/Sao_Paulo`.
- **Aspas simples**, PEP8, **Class Based Views** e recursos nativos do Django sempre que possível.
- Todo model herda `TimeStampedModel` (`created_at`, `updated_at`).
- Login por **email** (nunca username). Credenciais via `.env` + `django-environ` (ver `.env.example`).
- Signals em `signals.py` da app correspondente.
- Frontend: Django Templates + HTMX + Alpine.js + CSS do design system. Static via WhiteNoise. Mobile-first.
- **Proibido**: multi-tenant, Celery/RabbitMQ/Redis-broker, Docker Swarm/Traefik, LangChain/IA/OpenAI, trocar Django/PostgreSQL, over-engineering.
