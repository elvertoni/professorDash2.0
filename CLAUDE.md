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
- **Modo apresentação** (`AulaPresentationView`, rota `/turmas/<turma>/aulas/<pk>/apresentar/`): deck fullscreen da aula para TV de sala — capa hero + lightbox, quiz interativo com feedback, tipografia editorial. Mobile-first não se aplica aqui (alvo é tela grande).
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
