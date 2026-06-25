# AGENTS.md — Prof. Toni Coimbra

> Regras sempre ativas para qualquer agente de IA. Leitura obrigatória antes de codar. Detalhe em `PRD_PROF_DASH.md`; UI canônica em `design_system/design-system.html`; resumo de produto/design em `PRODUCT.md` e `DESIGN.md`; arquitetura operacional em `CLAUDE.md`.

## Fonte de verdade
- `PRD_PROF_DASH.md` = especificação (domínio, models, RF/RNF, pipeline de import, sprints). Código segue o PRD, nunca o contrário. **Estado das sprints = checklist da seção 9** — confira antes de iniciar qualquer sprint.
- `design_system/design-system.html` = UI obrigatória e fonte canônica do Design System v2 **"The Digital Atelier"**. NÃO invente componentes fora dele.
- `DESIGN.md` = índice resumido do design system, tokens, componentes, decisões de tema por papel e padrões ADHD-focus. Use para orientação rápida, mas confirme detalhes no HTML canônico.
- `PRODUCT.md` = contexto de produto, usuários, personalidade visual e princípios de UI/UX.
- `PRD_UI_UX_AJUSTE.md` = histórico do polish UI/UX, decisões D.1-D.9 e backlog visual. Consulte antes de mexer em telas.
- `CLAUDE.md` = arquitetura detalhada (apps, fluxos, convenções) — complementar a este arquivo.
- Antes de cada sprint ou mudança de UI: releia PRD + design system + `DESIGN.md` + código existente.
- Conflito → ordem: **regras invioláveis > design system > PRD > convenção Django**.

## O produto
Portal educacional **single-tenant** (Prof. Toni / SEED-PR, alunos 14-18). É a camada de entrega ao aluno do pipeline `canonica.md` (acervo PROF-TONI) → import → catálogo interno → publicação por turma → aluno. O portal consome o acervo, nunca o reescreve.

- **Professor** trabalha em lote: gerencia turmas/matrículas, sincroniza aulas, publica conteúdo, cria atividades de acompanhamento, marca checks por aluno e consulta relatórios.
- **Aluno** usa principalmente celular: abre o painel, vê o que fazer agora, estuda aulas disponíveis e acompanha progresso.
- **Entregas oficiais ficam no Google Classroom**. O portal não coleta entrega, arquivo, nota ou feedback de atividade.

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
- `catalog/import_acervo --path ../PROF-TONI [--only-aprovada] [--disciplina <slug>] [--force]` — idempotente por `(disciplina,trilha,ordem,slug)`; lê `manifesto.json` + `aulas/**/canonica.md`, converte blocos `:::conceito/:::atencao/:::dica`, diagramas e capa (`imagem:` ou `capa.{png,jpg,jpeg,webp}`). Detalhe na seção 6 do PRD.

Produção:
- Sistema em produção: `https://prof.tonicoimbra.com` via Easypanel (`projectName='work'`, `serviceName='professordash'`).
- Deploy atual = GitHub → Easypanel. Se precisar disparar manualmente, use o MCP Easypanel quando disponível (`deploy_service`).
- Validação final de mudança relevante deve considerar produção/VPS quando a tarefa pedir deploy ou correção pós-deploy.

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
9. **Media protegida**: `PROTECTED_MEDIA_ROOT` (raiz/`protected_media`) é separada de `MEDIA_ROOT` e **não tem URL pública**. Materiais servidos só por view com checagem de permissão (aluno da turma ou professor). Ver `base/storage.py`.
10. **SINGLE-TENANT**: sem campos/middleware de tenant. Escopo de visibilidade por `Matricula`/turma.
11. Frontend fixo: Django Templates + HTMX + Alpine.js + CSS do design system. Sem framework frontend pesado.
12. `Aula.imagem` (capa da aula) é pública em `MEDIA_ROOT`; materiais continuam protegidos. A capa vem do pipeline/import do acervo, não de IA dentro do portal.

## UI/UX obrigatório
- Identidade: Design System v2 **The Digital Atelier** — crafted, focused, editorial. Obsidian dark surfaces, tonal layering, glass sutil, Geist, Lucide icons, CTA emerald→cyan.
- Tema por papel: `base.html` renderiza `data-theme` por role (`aluno=light`, `professor/admin/anônimo=dark`). O toggle em `localStorage` pode sobrescrever como preferência do usuário.
- `Alpine.js 3.14.1` é dependência real do shell; `x-data`, `x-show`, `@click` e `[x-cloak]` dependem dele.
- Aluno é mobile-first: telas devem funcionar sem scroll horizontal a 360px, com cards escaneáveis, progresso visível e CTA inequívoco.
- Professor é desktop/denso: priorize trabalho em lote, accordions por série/disciplina, tabelas densas com `.tbl-wrap` quando necessário e ações agrupadas por intenção.
- Padrões ADHD-focus documentados em `DESIGN.md`: `serie-section`, `dash-collapsible`, `dash-tabs`, `aluno-progress`, `lesson-actionbar`. Objetivo: uma decisão por tela e próximo passo sempre visível.
- Componentes recorrentes devem existir no `design_system/design-system.html` antes de uso amplo. Proibido reintroduzir duplicatas `*-atelier`/`kpi-card` já unificadas.
- Cores têm função: verde = ação/progresso; amarelo = prazo/atenção; vermelho = risco; violeta/ciano = apoio.
- Acessibilidade mínima: contraste WCAG AA, foco visível, `scope="col"` em tabelas, erros com `aria-invalid`/`aria-describedby`/`role="alert"`, ícones decorativos com `aria-hidden="true"`, `prefers-reduced-motion`.
- Bans visuais: side-stripe border colorida, gradient text, glassmorphism decorativo como padrão, hero-metric template, grades de cards idênticos sem propósito, eyebrow em toda seção, marcadores `01/02/03` como andaime, texto estourando container, gradientes/hex literais em template quando existir token.

## Apps (todos na raiz, mesmo nível de `manage.py`)
- `core` — config do projeto (único `settings.py`, `urls.py`, view `/health/`).
- `base` — `TimeStampedModel` (abstract, herdado por todos), mixins de permissão, storage protegido, `HomeView`/`health`.
- `accounts` — `User` custom (login por email, `role`), `ProfessorProfile`, `AlunoProfile`, `signals.py`.
- `catalog` — `Disciplina`, `Trilha`, `Aula` (`conteudo_html`/`conteudo_md`/`imagem`); `import_acervo`, `parser.py`. Catálogo é depósito interno do acervo, não navegação principal do aluno/professor.
- `classroom` — `Turma`, `Matricula`, `AulaPublicada` (`disponivel_em`), `ProgressoAula`; `services.py`, `reports.py`; sincronização de aulas por turma/disciplina.
- `materials` — `Material` (FileField protegido ou link).
- `activities` — controle do professor (estilo Notion), **não entrega**: `Atividade` (`titulo`/`descricao`/`data`) + `AtividadeCheck` (`feito`+`observacao` por aluno). Entregas oficiais ficam no Google Classroom; `Entrega`/`EntregaArquivo` removidos.
- `notifications` — `Notificacao` (sino no header); `signals.py`, `context_processors.notification_summary` registrado em `settings.TEMPLATES`. Disparo ativo: aula publicada; eventos de entrega/correção não existem mais no fluxo do produto.

URLs prefixadas: `/conta/` `/catalogo/` `/turmas/` `/atividades/` `/materiais/` `/notificacoes/` `/health/`.

## Proibido
- Multi-tenant, Celery, RabbitMQ, Redis-broker, Docker Swarm, Traefik.
- LangChain/LangGraph/agentes de IA/OpenAI (fora desta fase).
- Pasta `apps/` ou `src/`. Renomear `core`/`base`. Múltiplos `settings.py`.
- Login por username. Models sem `created_at`/`updated_at`.
- Expor media sem checagem de permissão. Testes automatizados.
- Trocar Django/PostgreSQL. Over-engineering (abstrações sem necessidade).
- Inventar design system fora de `design_system/design-system.html`.
- Recriar fluxo de entrega/correção/nota no portal. Atividades são checks do professor; entrega oficial é Google Classroom.
- Recolocar `/catalogo/` como fluxo principal quando a jornada correta é sincronizar aulas dentro da turma.

## Fluxo de trabalho
- SPRINT-DRIVEN (seção 9 do PRD). Uma sprint por vez, em ordem. Definition of done = `[x]` no PRD.
- Estado atual documentado: Sprints 0-12 concluídas e redesign pós-lançamento registrado no PRD. Sempre confirme no PRD antes de iniciar.
- Ambiguidade: decida com best practice Django e **documente no PRD** (não em comentário solto).
- Git é do humano. NÃO commit/push a menos que pedido.
- Após sprint/tarefa: reporte o que foi feito, decisões e como validar manualmente. Para UI, inclua desktop/mobile e tema claro/escuro quando houver alteração visual.
