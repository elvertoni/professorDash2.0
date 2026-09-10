# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Regras do projeto (ler antes de codar)

As regras **invioláveis** estão em **[AGENTS.md](AGENTS.md)** — leitura obrigatória antes de qualquer tarefa. Fontes de verdade:

- `PRD_PROF_DASH.md` — especificação completa (domínio, models, RF/RNF, pipeline de import, deploy, roadmap de sprints §9).
- `design-system/design-system.html` — UI **obrigatória**. Não inventar componentes fora dele. Design System v3 **"Volta Atelier"** (brutalismo editorial: Archivo nos títulos, JetBrains Mono no corpo/metadados, acento `--signal` `#fb3732`, botões pílula com wipe hover). `design-system/volta-atelier.html` é a folha canônica do DS v3; `DESIGN.md` é o índice resumido; `PRD_UI_UX_AJUSTE.md` guarda o histórico de decisões visuais (D.1–D.14). **Nota**: `AGENTS.md` e `DESIGN.md` ainda citam o path antigo `design_system/` e "The Digital Atelier"/Geist — desatualizado; a verdade é `design-system/` + Volta Atelier.
- `PROMPT_BUILD_PROF_DASH.md` — prompt de build XML que rege o processo.

Antes de cada sprint: releia PRD + design system + código existente. Ordem em conflito: **regras invioláveis (AGENTS.md) > design system > PRD > convenção Django**.

## Estado atual

**Sistema em produção** em https://prof.tonicoimbra.com (Easypanel, projeto `work`, serviço `professordash`).

Sprints 0–12 concluídas + redesign pós-lançamento (foco TDAH) + redesign visual **Volta Atelier** aplicado em todo o projeto (commit `0d976de`). Apps ativos: `core`, `base`, `accounts`, `catalog`, `classroom`, `activities`, `materials`, `notifications`.

## Fluxo de trabalho (crítico)

- **Git é do humano**: NÃO commitar/push a menos que pedido.
- **Deploy** = push para GitHub → Easypanel auto-redeploy do serviço `professordash` (branch main).
- **Validação** = sempre na VPS via MCP Easypanel (`exec_in_container`) ou acessando https://prof.tonicoimbra.com. Nunca assumir que funciona sem checar em produção.
- **Sem testes automatizados** — proibido por decisão do PRD. Não rode `pytest`/`manage.py test` nem crie testes; valide manualmente e reporte os passos.
- Ambiguidade: decida com best practice Django e **documente no PRD** (não em comentário solto).
- Ao fim de cada tarefa: reporte o que foi feito, decisões e como validar na VPS. Para UI, cubra desktop/mobile e tema claro/escuro.

## Comandos

### VPS (produção — uso principal)

MCP Easypanel disponível. Padrão para rodar comandos Django em prod:

```
exec_in_container(projectName='work', serviceName='professordash', command='python manage.py <cmd>')
```

Exemplos: `python manage.py migrate` (aplicar migrations após deploy), `python manage.py shell -c "..."` (debug/consulta rápida).

Envs de produção ficam no Easypanel — ver/editar via `get_env_vars`/`set_env_var`. Deploy manual: `deploy_service(projectName='work', serviceName='professordash')`.

### Local (desenvolvimento de código)

Ambiente: `.venv` na raiz, Python >3.13, Django 6.0. Usar `uv` — a `.venv` **não tem `pip`**.

```powershell
.\.venv\Scripts\Activate.ps1
uv pip install --python .\.venv\Scripts\python.exe -r requirements.txt
python manage.py migrate
python manage.py runserver                # validação é manual, via navegador
python manage.py makemigrations <app>     # gerar migrations ANTES do push
docker compose up -d                      # dev: app + Postgres 17
```

**PostgreSQL é obrigatório**: `core/settings.py` usa `env.db('DATABASE_URL')` sem fallback — sem `.env` com `DATABASE_URL` válido o projeto não sobe. O `db.sqlite3` na raiz é artefato morto, não é usado. `settings.py` lê o `.env` da raiz quando o arquivo existe (settings.py:12-14), então dev local e produção compartilham o mesmo código de config.

### Management commands custom

| Comando | App | O que faz |
|---|---|---|
| `import_acervo --path ../PROF-TONI [--only-aprovada] [--disciplina <slug>] [--force]` | catalog | Importa o acervo local. **`--path` é obrigatório.** Idempotente por `(disciplina, trilha, ordem, slug)`. |
| `seed_demo [--password] [--reset-passwords]` | base | Dados fake de demonstração. |
| `test_email <dest>` | base | Testa SMTP em prod. |
| `import_students <arquivo.xlsx> [--dry-run]` | classroom | Cria turmas e matricula alunos a partir de planilha (openpyxl). O dict `DISCIPLINA_MAP` no topo do arquivo traduz rótulos da planilha → slugs de `Disciplina`. |
| `ensure_ai_turma [--professor-email ...]` | classroom | Garante a turma de Inteligência Artificial em produção. |
| `setup_tcc` | classroom | Cria turmas de TCC do 3º ano, matricula os mesmos alunos e publica as aulas. Exige `import_acervo` antes. |

**Email**: SMTP via env (`EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`). Sem `EMAIL_HOST` → fallback `console.EmailBackend`. Validar prod: `test_email`.

## Arquitetura

Portal educacional **single-tenant** (Prof. Toni / SEED-PR). É a camada de **entrega ao aluno** de um pipeline de conhecimento: `canonica.md` (acervo PROF-TONI) → import → catálogo → publicação por turma → aluno. O portal do Prof. Toni Coimbra **consome** o acervo, nunca o reescreve.

**Apps** (todos na raiz, mesmo nível de `manage.py` — proibido `apps/` ou `src/`):

| App | Responsabilidade | Peças-chave |
|---|---|---|
| `core` | Config do projeto (único `settings.py`, urls, `/health/`) | — |
| `base` | Recursos compartilhados | `TimeStampedModel` (abstract, herdado por *todos* os models), `storage.py` (media protegida), `views.py` (`HomeView`, `health`, `public_media`), `templatetags/form_extras.py` (`aria_field`) |
| `accounts` | Usuários, auth e **mixins de permissão** | `User` (custom, `email` = `USERNAME_FIELD`, `role` professor/aluno/admin), `ProfessorProfile`, `AlunoProfile`; `mixins.py`: `RoleRequiredMixin`, `ProfessorRequiredMixin`, `AlunoRequiredMixin`, `AdminRequiredMixin` |
| `catalog` | Taxonomia do acervo + **parser/renderer das aulas** | `Disciplina`, `Trilha`, `Aula` (`conteudo_html`/`conteudo_md`/`imagem`); `parser.py`, `services.py` |
| `classroom` | Turmas, publicação, modo apresentação, relatórios | `Turma`, `Matricula`, `AulaPublicada` (Aula→Turma com `disponivel_em`), `ProgressoAula`; `services.py` (import CSV de alunos), `reports.py` (PDF via reportlab + CSV) |
| `materials` | Materiais extras (upload manual) | `Material` (FileField protegido ou link) |
| `activities` | Controle de presença/tarefas do professor (estilo Notion) | `Atividade` (`titulo`/`descricao`/`data`), `AtividadeCheck` (`feito`+`observacao` por aluno). **Sem entrega/nota/arquivo** — entregas oficiais ficam no Google Classroom |
| `notifications` | Avisos in-app (sino no header) | `Notificacao` (só evento de aula publicada); `context_processors.notification_summary` registrado em `TEMPLATES` |

URLs prefixadas: `/conta/` `/catalogo/` `/turmas/` `/atividades/` `/materiais/` `/notificacoes/` `/health/` `/media/<path>`.

### Fluxos centrais

**Acervo → turma → aluno.** `import_acervo` lê `manifesto.json` + `aulas/{disciplina}/{trilha}/{NN-slug}/canonica.md` → `catalog/parser.py` → `Aula` (depósito interno; **catálogo fora do nav principal**). Alternativa sem repo local: `AcervoGithubImportView` (em `/catalogo/`, só admin) baixa o tarball do repo via `catalog/services.download_acervo`, configurado por `ACERVO_GITHUB_REPO` (default `elvertoni/head`), `ACERVO_GITHUB_REF`, `ACERVO_GITHUB_TOKEN`. Na turma, **Sincronizar aulas** (`TurmaSyncAulasView`) importa a disciplina da turma e publica tudo como `AulaPublicada` (disponível agora, idempotente). Aluno vê respeitando `disponivel_em`.

**Renderização da aula (`catalog/parser.py`).** O markdown canônico passa por várias etapas antes de virar HTML: frontmatter → wikilinks resolvidos contra os labels de conceito → fences customizados (`:::conceito/:::atencao/:::dica`, `diagram`, `quiz`) → figuras de `img/` → sanitização com **bleach** (allowlist de tags/atributos) → `scope="col"` normalizado em tabelas. `strip_teacher_notes`/`render_teacher_notes_html` separam a trilha do professor da do aluno. **`render_stored_lesson_html(aula)` é o ponto de entrada das views**: ele re-resolve os caminhos de imagem sobre o HTML já armazenado, então mexer em `MEDIA_URL`/layout de figura é aqui, não no import. `diagnostics=True` mostra notas de imagem faltando.

**Modo apresentação — "Leitura Projetada"** (`AulaPresentationView`, rota `/turmas/<turma>/aulas/<pk>/apresentar/`, template `classroom/aula_presentation.html`, motor `static/js/reader.js`, estilo `static/css/presentation.css`). A aula inteira rola em **coluna única**: sem fatiar em slides, sem medir, sem escalar — o conteúdo só rola, então nunca corta. Setas/Espaço/PageDown rolam ~90% da tela e pousam em um landmark próximo quando isso preserva o ritmo de leitura (teclado e controle remoto). Tem capa editorial com lightbox, barra de progresso de scroll e botão "Começar em tela cheia" (`F`). Este design **substituiu** o antigo deck fatiado com fit-to-stage/`--slide-scale`/auditor `?test=true` (`deck.js`, removido no commit `18feb21`) — não reintroduza aquele motor. Alvo é TV de sala; mobile-first não se aplica.

**Atividade → check.** Professor cria `Atividade` (item de controle) na turma → grade alunos×checkbox (`AtividadeChecksView`, bulk-save) marca `AtividadeCheck.feito` + observação. Não há entrega do aluno no portal.

### Regras transversais

- **Tema por papel**: aluno = `light`, professor/admin/anônimo = `dark` (server-rendered em `base.html`; toggle em `localStorage` sobrescreve — ver `static/js/app.js`).
- **Escopo de visibilidade** (em vez de tenant): aluno só enxerga turmas/aulas das suas `Matricula`; atividades são tela do professor. Toda rota privada exige auth + papel via os mixins de `accounts`.
- **Media — dois regimes, não confundir**:
  - *Protegida* (`PROTECTED_MEDIA_ROOT = protected_media/`, sem URL pública): materiais e uploads. Servidos só por view com checagem de permissão (aluno da turma ou professor). Ver `base/storage.py`.
  - *Pública* (`MEDIA_ROOT = media/`): capas e figuras de aula, vindas do import do acervo. Em produção **não há servidor de arquivos para `/media/`** — quem serve é `base.views.public_media`, com allowlist de prefixos: `catalog/capas/`, `catalog/imagens/` e `avatars/`. Qualquer outro caminho retorna 404. Foi exatamente esse o bug do commit `e535cf6` (figuras de miolo davam 404 para o aluno); ao adicionar um novo tipo de asset público, **atualize a allowlist**.
- **Frontend**: Django Templates + Alpine.js 3.14.1 (dependência real do shell — `x-data`/`x-show`/`@click`/`[x-cloak]`) + CSS do design system. HTMX é citado no PRD/AGENTS mas **não há uso real** nos templates hoje. Tudo **self-hosted** (sem CDN): Alpine e o subset de ícones Lucide em `static/js/vendor/` (`alpine-3.14.1.min.js`, `lucide-subset.js`), fontes em `static/fonts/` (`archivo-latin.woff2`, `jetbrains-mono-latin.woff2`; Geist fica só para a apresentação de aulas) — commit `d0b2ac7` removeu a dependência do Google Fonts CDN. `base.html` tem lógica de resiliência que detecta Alpine ausente/bloqueado. Static via WhiteNoise com `CompressedManifestStaticFilesStorage` (nomes com hash — sempre referencie por `{% static %}`).
- **CSS runtime**: `static/css/app.css` mapeia os tokens Volta Atelier (`--ink`, `--bone`, `--signal`, `--panel`, `--line`) para as variáveis retrocompatíveis do shell (`--surface-base`, `--fg`, `--accent`, `--border`…) — ver tabela em `DESIGN.md`. `presentation.css` é isolado para a Leitura Projetada. JS em `static/js/`: `app.js` (tema, lightbox, shell), `quiz.js` (componente Alpine `quizQuestion()`, usado nas páginas normais e no modo apresentação), `reader.js` (leitura projetada).
- **Cores têm função (Volta Atelier)**: `--signal` (vermelho `#fb3732`) = acento/ação primária/hover/alerta; `--amber` = prazo/atenção; `--emerald` = conclusão/checks/progresso; `--volt` (azul) = apoio/links complementares.

## Convenções de código

- Código em **inglês** (nomes, classes, variáveis). UI **100% pt-BR**. Timezone `America/Sao_Paulo`.
- **Aspas simples**, PEP8, **Class Based Views** e recursos nativos do Django sempre que possível.
- Todo model herda `TimeStampedModel` (`created_at`, `updated_at`).
- Login por **email** (nunca username). Credenciais via `.env` + `django-environ` (ver `.env.example`).
- Signals em `signals.py` da app correspondente.
- **Proibido**: multi-tenant, Celery/RabbitMQ/Redis-broker, Docker Swarm/Traefik, LangChain/IA/OpenAI, trocar Django/PostgreSQL, pasta `apps/`/`src/`, múltiplos `settings.py`, recriar fluxo de entrega/nota no portal, over-engineering.

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
