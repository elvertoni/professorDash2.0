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

> Management commands custom: `catalog/import_acervo` e `base/seed_demo`.

## Arquitetura

Portal educacional **single-tenant** (Prof. Toni / SEED-PR). É a camada de **entrega ao aluno** de um pipeline de conhecimento: `canonica.md` (acervo PROF-TONI) → import → catálogo → publicação por turma → aluno. O portal do Prof. Toni Coimbra **consome** o acervo, nunca o reescreve.

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
