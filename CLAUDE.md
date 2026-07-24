# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Regras do projeto (ler antes de codar)

As regras **invioláveis** estão em **[AGENTS.md](AGENTS.md)** — leitura obrigatória antes de qualquer tarefa. Fontes de verdade:

- `PRD_PROF_DASH.md` — especificação completa (domínio, models, RF/RNF, pipeline de import, deploy, roadmap de sprints §9).
- `design_system/design-system.html` — UI **obrigatória**. Não inventar componentes fora dele.
- `PROMPT_BUILD_PROF_DASH.md` — prompt de build XML que rege o processo.

Antes de cada sprint: releia PRD + design system + código existente. Ordem em conflito: **regras invioláveis (AGENTS.md) > design system > PRD > convenção Django**.

## Estado atual

**Sistema em produção** em https://prof.tonicoimbra.com (Easypanel, projeto `work`, serviço `professordash`).

Sprints 0–12 concluídas. Apps ativos: `core`, `base`, `accounts`, `catalog`, `classroom`, `activities`, `materials`, `notifications`.

## Fluxo de trabalho (crítico)

- **Git é do humano**: NÃO commitar/push a menos que pedido.
- **Deploy** = push para GitHub → Easypanel auto-redeploy do serviço `professordash` (branch main).
- **Validação** = sempre na VPS via MCP Easypanel (`exec_in_container`) ou acessando https://prof.tonicoimbra.com. Nunca assumir que funciona sem checar em produção.
- **Sem testes automatizados** — validação manual via VPS.
- Ambiguidade: decida com best practice Django e **documente no PRD** (não em comentário solto).
- Ao fim de cada tarefa: reporte o que foi feito, decisões e como validar na VPS.

## Comandos

### VPS (produção — uso principal)

MCP Easypanel disponível. Padrão para rodar comandos Django em prod:

```
exec_in_container(projectName='work', serviceName='professordash', command='python manage.py <cmd>')
```

Exemplos:
- `python manage.py migrate` — aplicar migrations após deploy
- `python manage.py shell -c "..."` — debug/consulta rápida
- `python manage.py import_acervo --only-aprovada` — reimportar acervo

Envs ficam no Easypanel (não há `.env` local em uso). Ver/editar via `get_env_vars`/`set_env_var`.

Deploy manual se necessário: `deploy_service(projectName='work', serviceName='professordash')`.

### Local (desenvolvimento de código)

Ambiente: `.venv` na raiz, Python >3.13, Django >6.0. Usar `uv` (não `pip` diretamente).

```powershell
.\.venv\Scripts\Activate.ps1
uv pip install --python .\.venv\Scripts\python.exe -r requirements.txt
python manage.py makemigrations <app>   # gerar migrations antes do push
```

> Management commands custom: `catalog/import_acervo`, `base/seed_demo`, `base/test_email <dest>` (testa SMTP).

**Email**: SMTP via env (`EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`). Sem `EMAIL_HOST` → fallback `console.EmailBackend` (settings.py:160). Validar prod: `test_email`.

## Arquitetura

Portal educacional **single-tenant** (Prof. Toni / SEED-PR). É a camada de **entrega ao aluno** de um pipeline de conhecimento: `canonica.md` (acervo PROF-TONI) → import → catálogo → publicação por turma → aluno. O portal do Prof. Toni Coimbra **consome** o acervo, nunca o reescreve.

**Apps** (todos na raiz, mesmo nível de `manage.py` — proibido `apps/` ou `src/`):

| App | Responsabilidade | Models-chave |
|---|---|---|
| `core` | Config do projeto (único `settings.py`, urls, `/health/`) | — |
| `base` | Recursos compartilhados | `TimeStampedModel` (abstract, herdado por *todos* os models), mixins de permissão, storage protegido de media |
| `accounts` | Usuários e auth | `User` (custom, `email` = `USERNAME_FIELD`, `role` professor/aluno/admin), `ProfessorProfile`, `AlunoProfile` |
| `catalog` | Taxonomia do acervo (espelha `manifesto.json`) | `Disciplina`, `Trilha`, `Aula` (canônica importada: `conteudo_html`/`conteudo_md`) |
| `classroom` | Turmas, publicação e modo apresentação | `Turma`, `Matricula`, `AulaPublicada` (Aula→Turma com `disponivel_em`), `ProgressoAula` |
| `materials` | Materiais extras (upload manual) | `Material` (FileField protegido ou link) |
| `activities` | Controle de presença/tarefas do professor (estilo Notion) | `Atividade` (item: `titulo`/`descricao`/`data`), `AtividadeCheck` (`feito`+`observacao` por aluno). **Sem entrega/nota/arquivo** — entregas oficiais ficam no Google Classroom |
| `notifications` | Avisos in-app (sino no header) | `Notificacao` (apenas eventos de aula publicada; entrega/correção foram removidos) |

**Fluxos centrais:**

- **Acervo → turma → aluno**: `import_acervo` lê `manifesto.json` + `aulas/{disciplina}/{trilha}/{NN-slug}/canonica.md` → parser custom → `Aula` (depósito interno; **catálogo fora do nav**). Na turma, o botão **Sincronizar aulas** (`TurmaSyncAulasView`) importa a disciplina da turma do head e publica todas como `AulaPublicada` (disponível agora, idempotente). Aluno vê respeitando `disponivel_em`.
- **Atividade → check**: professor cria `Atividade` (item de controle) na turma → grade alunos×checkbox (`AtividadeChecksView`, bulk-save) marca `AtividadeCheck.feito` + observação. Não há entrega do aluno no portal.
- **Modo apresentação** (`AulaPresentationView`, rota `/turmas/<turma>/aulas/<pk>/apresentar/`): deck fullscreen da aula para TV de sala. View server só entrega HTML sanitizado (`#deck-source`) + notas do professor; a montagem é client-side no **motor determinístico `static/js/deck.js`** — fatiamento estrutural (capa · uma seção por `h2`/`h3` com sua prosa/lista · blocos destaque `callout`/`quiz`/`table`/`code`/`media` cada um em slide próprio · encerramento) + **fit-to-stage** (escala única medida por slide, largura e altura, `--slide-scale`) que centraliza e encolhe sem cortar frase nem deixar slide oco. `ResizeObserver` re-ajusta quando o conteúdo muda (ex.: quiz revela feedback). Paginação só em fronteira de bloco quando algo não cabe nem no piso de escala (sem "continuação"). Splash de marca (`is-deck-loading`) cobre o palco até montar. Suite de teste visual: sufixo `?test=true` audita ocupação/overflow/erros por slide. Estilo em `static/css/presentation.css`. Mobile-first não se aplica (alvo é tela grande).
- **Tema por papel**: aluno = `light`, professor/admin = `dark` (server-rendered no `base.html`; toggle localStorage sobrescreve).
- **Escopo de visibilidade** (em vez de tenant): aluno só enxerga turmas/aulas das suas `Matricula`; atividades são tela do professor. Toda rota privada exige auth + papel.
- **Media protegida**: materiais NUNCA expostos publicamente — servidos via view com checagem de permissão (aluno da turma ou professor).

## Convenções de código

- Código em **inglês** (nomes, classes, variáveis). UI **100% pt-BR**. Timezone `America/Sao_Paulo`.
- **Aspas simples**, PEP8, **Class Based Views** e recursos nativos do Django sempre que possível.
- Todo model herda `TimeStampedModel` (`created_at`, `updated_at`).
- Login por **email** (nunca username). Credenciais via `.env` + `django-environ` (ver `.env.example`).
- Signals em `signals.py` da app correspondente.
- Frontend: Django Templates + HTMX + Alpine.js + CSS do design system. Static via WhiteNoise. Mobile-first.
- **Proibido**: multi-tenant, Celery/RabbitMQ/Redis-broker, Docker Swarm/Traefik, LangChain/IA/OpenAI, trocar Django/PostgreSQL, over-engineering.

<!-- ai-memory:start -->
## Long-term memory (ai-memory)

This project uses [ai-memory](https://github.com/akitaonrails/ai-memory)
for cross-session continuity.

**Default to the current project - always.** Every ai-memory tool
auto-scopes to the project resolved from your session's working
directory. **Do NOT pass `project`, `workspace`, or `cwd` arguments unless
the user explicitly references a *different* project by name** (e.g. "what
did we decide in the `other-app` project?"). Phrases like "this project",
"here", "we", "our work", and "where did we leave off" all mean the
*current* project, so call tools with no scoping args.

This default assumes the MCP client can identify the current agent
session. Static MCP clients in parallel sessions for the same user cannot
forward the real agent session id automatically; pass explicit
`workspace` + `project` / `scopes`, or use a session-aware bridge that
forwards the lifecycle-hook session id on MCP calls.

**Lifecycle hooks already capture sanitized, bounded prompt and tool-lifecycle
observations automatically.** They are not complete native transcripts;
managed `ai-memory run` launches add the portable visible-event ledger. Do not
manually write routine notes. Only write durable memory when the user explicitly asks
to remember or annotate something permanently.

### Use the installed ai-memory Agent Skills

Detailed tool-routing guidance lives in the installed ai-memory Agent
Skills. When a task matches an installed ai-memory Agent Skill, load and
follow that skill before calling ai-memory tools. The skills cover memory
retrieval, handoffs, durable pages, learning maintenance, and routing
install or refresh work.

### When you write a project rule, write it here

If you're about to write a durable project rule ("always X", "never
Y", "all PRs must ..."), write it in the project's canonical agent instruction file.
Many projects use CLAUDE.md for Claude Code and
AGENTS.md for Codex / OpenCode / Cursor / Gemini CLI / Grok Build CLI / Kimi Code,
but if the project says one file is canonical, use that file.

If the rule is a standing *user/team* preference that should apply to
every project (tech choices, code style, personal conventions), save it
to ai-memory's reserved global scope instead — the durable-pages skill
covers how. Default memory reads surface global-scope pages in every
project automatically.

### Refreshing this snippet

This block is maintained by ai-memory. Two ways to refresh it with the
latest binary's recommended copy:

- **From the agent** (no terminal needed): ask "refresh the ai-memory
  routing in this project". The agent calls `memory_install_self_routing`,
  picks the right filename for itself (Claude Code -> `CLAUDE.md`; Codex /
  OpenCode / Cursor / Gemini / Grok -> `AGENTS.md`; Kimi Code -> `AGENTS.md`),
  uses its Write / Edit tool to replace or append the returned
  `markered_block` while preserving
  non-ai-memory user content, then writes or updates each returned
  `managed_skills` item under the selected skill root from `target_hints`
  using its `relative_path`.
- **From the CLI**: `ai-memory install-instructions` (defaults to
  `CLAUDE.md`; pass `--target AGENTS.md` for non-Claude agents or projects
  that use `AGENTS.md` as the canonical instruction file).

Both are idempotent: re-runs replace the block delimited by the ai-memory
start/end HTML-comment markers, without disturbing the rest of the file.
<!-- ai-memory:end -->
