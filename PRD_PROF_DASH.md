# PRD — ProfessorDash (Portal do Aluno)

> Documento de Requisitos de Produto. Guia oficial do desenvolvimento do portal educacional ProfessorDash: a ponte entre o acervo de conhecimento do Prof. Toni Coimbra e o aluno.

---

## 1. Visão Geral

**ProfessorDash** é um portal educacional moderno onde o conhecimento construído no acervo PROF-TONI (aulas canônicas) chega ao aluno. O professor publica aulas por turma, cria atividades e corrige entregas; o aluno acessa aulas, faz atividades, entrega materiais e acompanha seu progresso.

Inspiração: melhores portais educacionais do mundo (Google Classroom, Khan Academy, Coursera, Canvas, Notion for Education) — impactante, moderno, fluido, focado na jornada do aluno.

### 1.1 Objetivo do produto

Ser a camada de **entrega ao aluno** do pipeline do segundo cérebro:

```
lake (bruto) → curadoria (skill prof-toni + rubrica) → warehouse (canonica.md) → SAÍDA: ProfessorDash
```

A `canonica.md` é a fonte de verdade. O ProfessorDash **consome** o acervo — não o reescreve.

### 1.2 Personas

| Persona | Quem é | Faz |
|---|---|---|
| **Professor** (Toni) | Dono do conteúdo, SEED-PR | Cria turmas, matricula alunos, publica aulas, cria atividades, dá check/nota/feedback nas entregas |
| **Aluno** | 14–18 anos, Curso Técnico em Desenvolvimento de Sistemas | Acessa aulas da sua turma, estuda, faz atividades, entrega materiais, vê notas e progresso |
| **Admin** | Toni (mesmo) | Gestão total via Django Admin |

### 1.3 Decisões de produto (definidas)

- **Tenancy:** Single-tenant. Uma instalação para o Prof. Toni (SEED-PR). Sem isolamento por escola. Simplicidade total.
- **Pipeline de aulas:** **Os dois** — importação automática do acervo (`canonica.md` / HTML) **e** upload manual de materiais extras por turma/aula.
- **Infra:** **Simplificada** — Django + PostgreSQL + Docker Compose + reverse proxy (Caddy). Sem Swarm, sem Celery/RabbitMQ/Redis-broker.
- **IA:** **Nenhuma por enquanto.** Foco no core. IA fica para fase futura (removidos Celery, broker, Langchain do escopo).

---

## 2. Tech Specs

- Python `>3.13`. Ambiente virtual em `.venv` na raiz. `requirements.txt` sempre atualizado na raiz.
- Framework **Django `>6.0`**.
- **Single-tenant** — sem campos de tenant, sem middleware de separação por corretora. Apenas escopo de visibilidade por turma/matrícula.
- Autenticação: sistema nativo do Django. **Login por email** (não username).
- Disparo de emails: sistema nativo do Django (recuperação de senha, notificação de matrícula). Config no `.env` → `settings.py`.
- Entidades/domínios separados em **apps Django** (uma responsabilidade por app). Apps na raiz do projeto.
  - App principal: **`core`**.
  - App de recursos base/compartilhados: **`base`**.
- Código em **inglês**; aspas simples; PEP8. UI 100% em **português brasileiro**. Timezone `America/Sao_Paulo`.
- Toda tabela/model tem `created_at` e `updated_at` (mixin em `base`).
- **Não implementar testes** (decisão do projeto; rever se virar SaaS).
- Credenciais em `.env` na raiz (gitignored), importadas no `settings.py` via `django-environ`.
- **Um único** `settings.py`.
- Banco: **PostgreSQL**.
- Docker + Docker Compose para rodar local **e** em produção (VPS). **Sem Docker Swarm.**
- **Sem Celery/RabbitMQ/Redis-broker** nesta fase (não há tarefas pesadas/IA). Cache via `LocMemCache` ou Redis simples opcional.
- Sempre que possível, **Class Based Views** e recursos nativos do Django.
- Signals (se houver) em `signals.py` da app correspondente.
- **Reportlab + PyPDF** para relatórios (boletim, relatório de turma) em PDF.
- Pasta `docs/` com documentação sempre atualizada, servida via **MkDocs** (com suporte a mermaid).
- Django command de **carga inicial de dados fakes** (seed): turmas, alunos, aulas importadas, atividades, entregas em datas variadas — para demonstração.
- **Design system** referenciado em `design_system/design-system.html`. Todo design (cores, componentes, tipografia) respeita rigorosamente o design system.
- Proteção de media: arquivos de materiais/entregas servidos **somente** a usuários com permissão (aluno da turma ou professor). Nunca expor media publicamente.

### 2.1 Stack resumido

| Camada | Tecnologia |
|---|---|
| Backend | Django >6.0, Python >3.13 |
| Banco | PostgreSQL |
| Frontend | Django Templates + HTMX + Alpine.js + Tailwind (ou CSS do design system) |
| Render de aula | Markdown → HTML (parser custom dos blocos `:::tipo`) ou HTML standalone importado |
| Static | WhiteNoise |
| Reverse proxy / TLS | Caddy (HTTPS automático via Let's Encrypt) |
| Containers | Docker + Docker Compose |
| Docs | MkDocs + mermaid |
| Relatórios | Reportlab + PyPDF |

---

## 3. Modelo de Domínio

Apps Django e principais models:

### 3.1 App `base`
- `TimeStampedModel` (abstract): `created_at`, `updated_at`. Herdado por todos os models.
- Helpers compartilhados, mixins de permissão, storage protegido de media.

### 3.2 App `accounts` (usuários)
- `User` (custom, `AbstractUser` com `email` como `USERNAME_FIELD`): `role` (`professor` | `aluno` | `admin`), `nome_completo`, `avatar`.
- `ProfessorProfile`: vínculo SEED, disciplinas que leciona.
- `AlunoProfile`: matrícula escolar, série, responsável (opcional), data de nascimento.

### 3.3 App `catalog` (taxonomia do acervo — espelha o manifesto)
- `Disciplina`: `slug`, `label`, `serie`, `status`. (espelha `manifesto.json`)
- `Trilha`: `disciplina` (FK), `slug`, `label`.
- `Aula` (lesson canônica importada):
  - `disciplina` (FK), `trilha` (FK), `ordem` (int), `slug`, `titulo`, `tema`.
  - `objetivos` (JSON), `prerequisitos` (JSON), `modo_origem`.
  - `conteudo_html` (TextField — corpo da canônica renderizado), `conteudo_md` (fonte original).
  - `html_standalone` (FileField opcional — saída da skill `aula-estatica`).
  - `status` (`aprovada` | `planejada` | ...), `versao`, `atualizado_em`, `source_path`.
  - Importadas apenas com `status = aprovada`.

### 3.4 App `classroom` (turmas)
- `Turma`: `nome`, `disciplina` (FK), `serie`, `ano_letivo`, `professor` (FK), `codigo_convite`, `ativa`.
- `Matricula`: `turma` (FK), `aluno` (FK User), `data_matricula`, `status` (`ativa` | `inativa`).
- `AulaPublicada`: vincula `Aula` (catálogo) → `Turma`, com `disponivel_em` (data de liberação), `ordem_na_turma`, `publicada` (bool). É como uma aula do acervo "aparece" para a turma.
- `ProgressoAula`: `aluno`, `aula_publicada`, `visto_em`, `concluido` (bool). Aluno marca conclusão / progresso.

### 3.5 App `materials` (materiais extras)
- `Material`: `turma` (FK, opcional), `aula_publicada` (FK, opcional), `titulo`, `descricao`, `arquivo` (FileField protegido) ou `link_externo`, `tipo` (pdf | slide | link | video | outro), `enviado_por` (FK professor).

### 3.6 App `activities` (atividades e entregas)
- `Atividade`: `turma` (FK), `aula_publicada` (FK, opcional), `titulo`, `enunciado` (markdown→html), `anexos` (M2M Material), `prazo` (datetime), `pontuacao_max`, `permite_entrega_atrasada`, `publicada`.
- `Entrega` (submission): `atividade` (FK), `aluno` (FK), `texto_resposta`, `data_entrega`, `status` (`pendente` | `entregue` | `atrasada` | `corrigida`).
- `EntregaArquivo`: `entrega` (FK), `arquivo` (FileField protegido).
- **Correção (o "check" do professor):** na `Entrega` → `nota`, `feedback`, `corrigido_por`, `corrigido_em`, `checked` (bool). Professor dá check/nota/feedback.

### 3.7 App `notifications`
- `Notificacao`: `usuario` (FK), `titulo`, `mensagem`, `link`, `lida` (bool), `tipo`. In-app (sino no header). Disparada em: nova aula publicada, nova atividade, prazo próximo, entrega corrigida.

### 3.8 Diagrama de relacionamento (resumo)

```mermaid
erDiagram
    User ||--o{ Matricula : "aluno"
    User ||--o{ Turma : "professor"
    Turma ||--o{ Matricula : tem
    Turma ||--o{ AulaPublicada : publica
    Aula ||--o{ AulaPublicada : origem
    Disciplina ||--o{ Trilha : tem
    Trilha ||--o{ Aula : agrupa
    AulaPublicada ||--o{ ProgressoAula : acompanha
    Turma ||--o{ Atividade : tem
    Atividade ||--o{ Entrega : recebe
    User ||--o{ Entrega : "aluno"
    Entrega ||--o{ EntregaArquivo : anexa
    Turma ||--o{ Material : tem
```

---

## 4. Requisitos Funcionais

### 4.1 Autenticação e contas
- [ ] Login por email + senha.
- [ ] Recuperação de senha por email (nativo Django).
- [ ] Perfis: professor e aluno com telas e permissões distintas.
- [ ] Edição de perfil (nome, avatar, senha).

### 4.2 Landing page
- [ ] Página raiz com apresentação do portal, identidade visual do design system.
- [ ] CTA para login. (Cadastro de aluno é feito pelo professor / por código de convite — não auto-registro aberto, já que é single-tenant SEED.)
- [ ] Responsiva e impactante.

### 4.3 Gestão (professor)
- [ ] CRUD de **Turmas** (nome, disciplina, série, ano letivo, código de convite).
- [ ] CRUD de **Alunos** + matrícula em turma. Importação de alunos via CSV.
- [ ] CRUD de **Professores** (caso outros profs usem; admin gerencia).
- [ ] Matricular/desmatricular aluno em turma.

### 4.4 Catálogo e publicação de aulas
- [ ] **Importar aulas do acervo** (Django command — ver §6). Catálogo de aulas aprovadas, navegável por disciplina/trilha/ordem.
- [ ] **Publicar aula em turma**: professor escolhe aulas do catálogo, define data de liberação (`disponivel_em`) e ordem na turma.
- [ ] Despublicar / reordenar aulas da turma.

### 4.5 Experiência do aluno
- [ ] **Dashboard do aluno**: minhas turmas, próximas aulas liberadas, atividades pendentes e prazos, últimas notas.
- [ ] **Visualizar aula**: render rico da `canonica.md` (blocos `:::conceito`, `:::atencao`, `:::dica`, diagramas) fiel ao design system. Navegação anterior/próxima dentro da trilha da turma.
- [ ] **Marcar aula como concluída** (progresso).
- [ ] **Materiais da aula/turma**: baixar arquivos protegidos, acessar links.
- [ ] **Fazer e entregar atividade**: texto + upload de arquivos. Respeita prazo (marca atrasada se permitido).
- [ ] **Ver notas e feedback** das entregas corrigidas.
- [ ] **Notificações** in-app.

### 4.6 Correção (professor)
- [ ] Listar entregas por atividade/turma, com status (pendente/entregue/atrasada/corrigida).
- [ ] Abrir entrega: ver texto + baixar arquivos do aluno.
- [ ] **Dar check**: lançar nota, escrever feedback, marcar como corrigida. Dispara notificação ao aluno.
- [ ] Visão de "atividades aguardando correção" no dashboard do professor.

### 4.7 Dashboard do professor
- [ ] Visão geral: nº de turmas, alunos, atividades, entregas pendentes de correção.
- [ ] Gráficos: entregas por turma, taxa de conclusão de aulas, notas médias, prazos próximos.
- [ ] Acesso rápido a turmas e correções.

### 4.8 Materiais
- [ ] Upload de materiais por turma e/ou aula (PDF, slides, links, vídeos).
- [ ] Download protegido por permissão (somente turma/professor).

### 4.9 Relatórios
- [ ] Boletim do aluno (PDF) — notas por atividade/turma.
- [ ] Relatório de turma (PDF/CSV) — matrículas, progresso, médias.

### 4.10 Admin Django
- [ ] Gestão de todas as entidades com filtros (turmas, alunos, aulas, atividades, entregas, materiais, notificações).

---

## 5. Requisitos Não Funcionais

- [ ] **Responsivo** em todos os tamanhos de tela (mobile-first — alunos usam celular).
- [ ] **Seguro**: rotas fechadas por autenticação e papel; aluno só vê suas turmas/aulas/atividades; media protegida (entregas e materiais nunca expostos publicamente).
- [ ] **UI/UX excelente** fiel ao design system; bom contraste; jornadas fluidas. Inspiração nos melhores portais educacionais.
- [ ] **Performance**: filtros e telas rápidos; paginação; `select_related`/`prefetch_related`; nada bloqueante.
- [ ] **Acessibilidade** básica (semântica, contraste, navegação por teclado).
- [ ] **Deploy resiliente** mas simples: Docker Compose com `restart: unless-stopped`, healthchecks de app e banco, volumes nomeados para persistência (postgres, media, staticfiles).
- [ ] **Backup**: script `scripts/backup.sh` do PostgreSQL e da media, com rotação por tempo.
- [ ] **Segredos** de produção fora do versionamento (`.env` gitignored na VPS).
- [ ] `collectstatic --clear` no entrypoint para evitar arquivos hash obsoletos (WhiteNoise).

---

## 6. Pipeline de Importação do Acervo

O diferencial do ProfessorDash: ele lê o warehouse do segundo cérebro.

### 6.1 Estrutura de origem (este repositório PROF-TONI)
- Índice: `manifesto.json` → `disciplinas[]` e `lessons[]` (disciplina, trilha, ordem, titulo, slug, status).
- Conteúdo: `aulas/{disciplina}/{trilha}/{NN-slug}/canonica.md`.
- `canonica.md` = frontmatter YAML (`titulo`, `tema`, `disciplina`, `serie`, `prerequisitos`, `objetivos`, `trilha`, `ordem`, `status`, `versao`, `atualizado_em`) + corpo Markdown com blocos custom `:::conceito`, `:::atencao`, `:::dica` e fences de diagrama (`diagrama-progressivo`, etc.).
- Saída opcional já renderizada: skill `aula-estatica` gera HTML standalone (CSS/JS/SVG embutidos).

### 6.2 Django command `import_acervo`
```
python manage.py import_acervo --path /caminho/para/PROF-TONI [--only-aprovada] [--disciplina inteligencia-artificial]
```
- [ ] Lê `manifesto.json` → cria/atualiza `Disciplina` e `Trilha`.
- [ ] Para cada lesson `status = aprovada`: lê `canonica.md`, faz parse do frontmatter YAML.
- [ ] Converte o corpo Markdown (incluindo blocos `:::tipo` e diagramas) para `conteudo_html` via parser custom (reaproveitar a lógica de render da skill `aula-estatica`).
- [ ] Cria/atualiza `Aula` casando por `(disciplina, trilha, ordem, slug)`. **Idempotente**: só atualiza se `versao`/`atualizado_em` mudou.
- [ ] Opcional: importar o HTML standalone como `html_standalone`.
- [ ] Relatório ao final: criadas / atualizadas / ignoradas.

### 6.3 Estratégia de integração (origem dos arquivos)
- **Fase 1 (MVP):** importação por path local (rodar o command apontando para o repo PROF-TONI clonado no servidor).
- **Fase 2 (futuro):** sincronização via Git (pull do repo) ou upload de pacote `.zip` do acervo pelo admin.

### 6.4 Upload manual (complementa o import)
- [ ] Professor envia materiais extras (PDFs, slides, links) por turma/aula direto na interface — independente do acervo.

---

## 7. Design System & UX

- [ ] Seguir rigorosamente `design_system/design-system.html` (cores, tipografia, componentes).
- [ ] Tema claro/escuro (o acervo já produz HTML com dark/light — manter coerência).
- [ ] Componentes-chave: card de turma, card de aula (com progresso), card de atividade (com prazo/status), visualizador de aula, área de entrega, sino de notificações, tabela de correção.
- [ ] Referências de excelência: Google Classroom (simplicidade), Khan Academy (progresso/gamificação leve), Coursera/Canvas (estrutura de curso), Notion (leitura limpa de conteúdo).
- [ ] Microinterações e feedback visual em ações (entrega enviada, atividade corrigida).

---

## 8. Guia de Deploy (VPS Ubuntu, do zero)

Deploy simplificado com **Docker Compose + Caddy** (HTTPS automático). Sem Swarm.

> Domínio: `prof.tonicoimbra.com`. Ajustar DNS no Cloudflare apontando A/AAAA para o IP da VPS.

### 8.1 Preparar a VPS
```bash
# 1. Acesso e atualização
ssh root@SEU_IP
apt update && apt upgrade -y

# 2. Usuário não-root (opcional, recomendado)
adduser deploy && usermod -aG sudo deploy

# 3. Instalar Docker + Compose plugin
curl -fsSL https://get.docker.com | sh
apt install -y docker-compose-plugin
docker --version && docker compose version

# 4. Firewall
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw enable
```

### 8.2 DNS (Cloudflare)
- [ ] Criar registro **A** `prof.tonicoimbra.com` → IP da VPS.
- [ ] (Caddy resolve o TLS via HTTP-01 automaticamente — sem token, sem wildcard. Se quiser wildcard, usar DNS-01 com plugin Cloudflare e um token de API escopo `Zone > DNS > Edit`.)

### 8.3 Código e variáveis
```bash
# Clonar o projeto do portal
git clone git@github.com:elvertoni/professordash.git /opt/professordash
cd /opt/professordash

# Clonar o acervo (fonte das aulas) para importar depois
git clone git@github.com:elvertoni/PROF-TONI.git /opt/acervo

# Criar .env de produção (gitignored)
cp .env.example .env
nano .env
```
`.env` de produção (exemplo):
```
DEBUG=False
SECRET_KEY=<gerar>
ALLOWED_HOSTS=prof.tonicoimbra.com,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://prof.tonicoimbra.com
DATABASE_URL=postgres://professordash:SENHA@db:5432/professordash
EMAIL_HOST=...
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
```
> `ALLOWED_HOSTS` só hostname (sem esquema). `CSRF_TRUSTED_ORIGINS` com `https://`. `localhost`/`127.0.0.1` necessários para o healthcheck interno.

### 8.4 Subir o stack
```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps   # checar healthchecks
docker compose -f docker-compose.prod.yml logs -f caddy   # verificar emissão TLS
```

### 8.5 Inicialização do app
```bash
# Migrations + superuser + estáticos rodam no entrypoint; criar admin:
docker compose -f docker-compose.prod.yml exec app python manage.py createsuperuser

# Importar as aulas do acervo
docker compose -f docker-compose.prod.yml exec app \
  python manage.py import_acervo --path /acervo --only-aprovada
```

### 8.6 Serviços do `docker-compose.prod.yml`
- `app` — Django (Gunicorn), healthcheck em `/health/`, `restart: unless-stopped`.
- `db` — PostgreSQL, healthcheck `pg_isready`, volume nomeado.
- `caddy` — reverse proxy + HTTPS automático, volumes para certificados.
- (acervo montado como volume read-only em `/acervo` para o import.)

Volumes nomeados: `pgdata`, `media`, `staticfiles`, `caddy_data`, `caddy_config`.

### 8.7 Healthcheck
- [ ] Endpoint `/health/` retorna 200 sem tocar o banco e sem auth (usado pelo HEALTHCHECK do container).
- [ ] Entrypoint do `app`: `wait_for_db` → `migrate` → `collectstatic --clear` → Gunicorn.

### 8.8 Backup
```bash
# scripts/backup.sh — dump do Postgres + tar da media, com rotação por tempo
0 3 * * * /opt/professordash/scripts/backup.sh   # cron diário 03:00
```

### 8.9 Atualização (redeploy)
```bash
cd /opt/professordash && git pull
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 9. Sprints de Desenvolvimento (checklist)

> Marque `[x]` ao concluir. Ordem lógica: fundação → domínio → aluno → professor → polish → deploy.

### Sprint 0 — Fundação do projeto
- [ ] Criar repositório `professordash` e estrutura Django (`core`, `base`).
- [ ] `.venv`, `requirements.txt`, `django-environ`, `.env.example`.
- [ ] `settings.py` único (DEBUG, ALLOWED_HOSTS, CSRF, DATABASE_URL, email, timezone, idioma).
- [ ] `TimeStampedModel` em `base` + storage protegido de media.
- [ ] Docker Compose de desenvolvimento (app + Postgres).
- [ ] Endpoint `/health/`.
- [ ] Integrar design system (`design_system/design-system.html`) ao base template.

### Sprint 1 — Contas e autenticação
- [ ] App `accounts`: `User` custom com login por email, `role`.
- [ ] `ProfessorProfile`, `AlunoProfile`.
- [ ] Telas de login, logout, recuperação de senha (email).
- [ ] Edição de perfil.
- [ ] Permissões/mixins por papel (professor vs aluno).
- [ ] Django Admin de usuários.

### Sprint 2 — Catálogo e importação do acervo
- [ ] App `catalog`: models `Disciplina`, `Trilha`, `Aula`.
- [ ] Parser de frontmatter YAML + Markdown→HTML dos blocos `:::tipo` e diagramas.
- [ ] Command `import_acervo` (idempotente, `--only-aprovada`).
- [ ] Tela de catálogo de aulas (navegável por disciplina/trilha/ordem).
- [ ] Visualizador de aula (render fiel ao design system).

### Sprint 3 — Turmas e matrículas
- [ ] App `classroom`: `Turma`, `Matricula`.
- [ ] CRUD de turmas (professor).
- [ ] CRUD de alunos + matrícula; importação CSV de alunos.
- [ ] Código de convite para turma.
- [ ] Admin de turmas/matrículas.

### Sprint 4 — Publicação de aulas por turma
- [ ] `AulaPublicada` (aula do catálogo → turma, com `disponivel_em` e ordem).
- [ ] Tela do professor para publicar/reordenar/despublicar aulas na turma.
- [ ] `ProgressoAula` (aluno marca conclusão).
- [ ] Lista de aulas da turma para o aluno, respeitando data de liberação.

### Sprint 5 — Experiência do aluno
- [ ] Dashboard do aluno (turmas, próximas aulas, atividades, notas).
- [ ] Visualizar aula publicada + navegação anterior/próxima.
- [ ] Marcar conclusão de aula.
- [ ] Responsividade mobile-first.

### Sprint 6 — Atividades e entregas
- [ ] App `activities`: `Atividade`, `Entrega`, `EntregaArquivo`.
- [ ] Professor cria atividade (vinculada a turma/aula, prazo, pontuação).
- [ ] Aluno entrega (texto + arquivos), respeitando prazo/atraso.
- [ ] Lista de entregas para o professor (status).

### Sprint 7 — Correção (o "check")
- [ ] Tela de correção: ver entrega, baixar arquivos, lançar nota + feedback, marcar corrigida.
- [ ] Aluno vê nota e feedback.
- [ ] Visão de "aguardando correção" no dashboard do professor.

### Sprint 8 — Materiais e media protegida
- [ ] App `materials`: `Material` (upload por turma/aula, links).
- [ ] Download protegido por permissão (turma/professor).
- [ ] Anexar materiais a atividades.

### Sprint 9 — Notificações
- [ ] App `notifications`: `Notificacao` + sino no header.
- [ ] Disparos: nova aula publicada, nova atividade, prazo próximo, entrega corrigida.
- [ ] Marcar como lida.

### Sprint 10 — Dashboards e relatórios
- [ ] Dashboard do professor (métricas + gráficos).
- [ ] Boletim do aluno (PDF, Reportlab).
- [ ] Relatório de turma (PDF/CSV).

### Sprint 11 — Seed e documentação
- [ ] Command de carga de dados fakes (turmas, alunos, aulas, atividades, entregas em datas variadas).
- [ ] `docs/` com MkDocs + mermaid (arquitetura, deploy, uso).

### Sprint 12 — Deploy em produção
- [ ] `docker-compose.prod.yml` (app + db + caddy) com healthchecks e volumes.
- [ ] Entrypoint (`wait_for_db` → migrate → collectstatic --clear → gunicorn).
- [ ] Caddy com HTTPS automático no domínio.
- [ ] `scripts/backup.sh` + cron.
- [ ] Importar acervo em produção e validar render das aulas.
- [ ] Smoke test completo das jornadas (professor e aluno).

---

## 10. Fora de Escopo (fases futuras)

- IA (tutor do aluno, assistente do professor) — reintroduz Celery/broker/Langchain.
- Multi-tenant / SaaS para outras escolas.
- Pagamentos e planos.
- Gamificação avançada (badges, ranking).
- App mobile nativo.
- Sincronização automática do acervo via webhook/CI.

---

## 11. Glossário

| Termo | Significado |
|---|---|
| **Acervo / Warehouse** | Repositório PROF-TONI com as `canonica.md` (fonte de verdade) |
| **Canônica** | Aula impecável em Markdown, fonte única de verdade |
| **Aula publicada** | Aula do catálogo liberada para uma turma específica |
| **Check** | Ato do professor de corrigir uma entrega (nota + feedback) |
| **Single-tenant** | Uma instalação, um professor/instituição (sem isolamento por escola) |
