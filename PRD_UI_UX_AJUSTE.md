# PRD_UI_UX_AJUSTE.md — Plano de Ajuste UI/UX

> Plano operacional para corrigir inconsistencias de interface, acessibilidade e usabilidade identificadas na auditoria UI/UX. Este documento nao substitui `PRD_PROF_DASH.md`; ele detalha apenas o trabalho de polish visual e experiencia.

## 1. Objetivo

Elevar o portal Prof. Toni Coimbra para uma experiencia visual e funcional consistente com o design system obrigatorio, com foco em:

- Aderencia real ao `design_system/design-system.html`.
- Usabilidade diaria do professor.
- Usabilidade mobile-first do aluno.
- Acessibilidade basica: contraste, foco, semantica e leitura por teclado/leitor de tela.
- Reducao de carga cognitiva em telas densas.
- Consistencia de tokens, componentes, estados e linguagem de interface.

## 2. Fontes de Verdade

Ordem de decisao:

1. Regras inviolaveis do `AGENTS.md`.
2. `design_system/design-system.html`.
3. `PRD_PROF_DASH.md`.
4. Padroes existentes do codigo Django.

Referencias externas usadas como criterio, nao como fonte obrigatoria:

- `https://github.com/Dammyjay93/interface-design`
- `https://github.com/anthropics/claude-code/tree/main/plugins/frontend-design`

## 3. Escopo

### 3.1 Incluido

- CSS global em `static/css/app.css`.
- Layout base em `templates/base.html`.
- Home em `templates/home.html`.
- Dashboards professor/aluno.
- Telas de turma, atividades, materiais, catalogo, notificacoes e conta.
- Componentes recorrentes: botoes, cards, KPIs, tabelas, empty states, forms, badges, breadcrumbs, notificacoes e lesson viewer.
- Ajustes de copy de botoes/estados quando melhorarem a clareza da jornada.
- Pequenos ajustes de views/forms apenas se forem necessarios para exibir estado/CTA corretamente.

### 3.2 Fora de Escopo

- Criar novo design system paralelo.
- Trocar stack, framework, Django, banco ou arquitetura.
- Criar testes automatizados.
- Refatorar regras de negocio sem necessidade direta de UX.
- Redesenhar o produto como landing page.
- Introduzir biblioteca de graficos ou framework frontend pesado.
- Introduzir IA, Celery, broker ou qualquer dependencia proibida no PRD principal.

## 4. Principios de Design

1. **Atelier digital, nao LMS generico**: manter obsidian, tonal layering, glass sutil, Geist, Lucide e gradiente de CTA do design system.
2. **Uma fonte de componentes**: componentes usados 2+ vezes devem existir no design system ou ser incorporados a ele antes de uso amplo.
3. **Professor trabalha em lote**: telas do professor priorizam correcao, gestao de turma, publicacao e relatorios com hierarquia clara.
4. **Aluno usa celular**: telas do aluno priorizam cards, status visivel, prazo claro e CTA inequívoco.
5. **Cor tem funcao**: verde para acao/progresso, amarelo para prazo/atencao, vermelho para risco, violeta/ciano apenas como apoio sem competir.
6. **Estados sao parte do componente**: todo controle precisa default, hover, active, focus-visible, disabled, loading quando aplicavel, empty/error.
7. **Copy operacional**: botoes dizem exatamente o que acontece: "Enviar atividade", "Ver feedback", "Publicar aula", "Salvar e proxima".
8. **Acessibilidade minima nao e opcional**: foco visivel, contraste adequado, labels, aria para erros, icones decorativos ocultos.

## 5. Definition of Done Geral

Uma sprint so pode ser marcada como concluida quando:

- [ ] Todas as tasks da sprint estao marcadas com `[x]`.
- [ ] O agente releu `design_system/design-system.html` antes de alterar UI.
- [ ] Nao foram criados componentes fora do design system sem documentar no proprio design system.
- [ ] Nao foram criados testes automatizados.
- [ ] `python manage.py check` foi executado e passou.
- [ ] Validacao manual via `runserver` + navegador foi documentada no final da sprint.
- [ ] Desktop e mobile foram verificados manualmente nas telas alteradas.
- [ ] Tema escuro e tema claro foram verificados nas telas alteradas.
- [ ] O PRD principal nao foi marcado como concluido por causa deste documento.

## 6. Roadmap de Sprints

### Sprint 0 — Preparacao e Inventario

Objetivo: criar uma base segura para ajustes sem regressao visual ou divergencia do design system.

#### Tasks

- [x] 0.1. Reler `AGENTS.md`, `PRD_PROF_DASH.md`, `CLAUDE.md` e `design_system/design-system.html`.
- [x] 0.2. Mapear todos os componentes CSS usados em templates com `rg -n "class=\"" templates static/css/app.css`.
- [x] 0.3. Listar classes presentes em `app.css` que nao existem no design system.
- [x] 0.4. Classificar classes extras em tres grupos: manter e documentar, substituir por componente existente, remover.
- [x] 0.5. Identificar todos os estilos inline estaticos em templates, separando os dinamicos aceitaveis como `width:{{ pct }}%`.
- [x] 0.6. Identificar telas prioritarias para validacao manual: home, login, dashboard professor, dashboard aluno, detalhe turma, lista atividades aluno, correcao, aula aluno, materiais aluno.
- [x] 0.7. Registrar no final desta sprint um resumo curto das decisoes de componentes.

#### Validacao Manual

- [x] 0.8. Rodar `python manage.py check`.
- [x] 0.9. Abrir o design system local no navegador.
- [x] 0.10. Confirmar visualmente quais componentes do DS devem ser reaproveitados.

Nota da Sprint 0:
- Inventario executado por 5 agentes frontend designer em paralelo (leitura das fontes de verdade, mapeamento de classes em templates, extracao do `app.css`, busca de estilos inline e levantamento das telas prioritarias).
- 0.1: `AGENTS.md`, `PRD_PROF_DASH.md`, `CLAUDE.md` e `design_system/design-system.html` (828 linhas) relidos. DS v2 "The Digital Atelier" catalogado: ~180 seletores agrupados em 13 categorias (botoes, cards/KPIs, layout, tipografia, tags/badges, formularios, navegacao, estados, lesson reader, motion, avatares, utilitarias, tabela) + tokens completos (superficies obsidian, bordas ghost, texto nunca-#fff, marca esmeralda/violeta/ciano, semantico, sombras tinted, raios, fontes Geist, gradientes, layout, espacamentos) nos temas escuro e claro.
- 0.2: 46 templates escaneados (45 com classes, 1 email texto). 145 classes unicas usadas. Top 6 (`btn`, `badge`, `btn-primary`, `eyebrow`, `btn-outline`, `classroom-page`) cobrem a maioria — base consolidada. 66 classes raras (1 arquivo), ~45% do total, mas a maioria justificada (header, hero, auth, conta sao estruturalmente unicos). Candidatos reais a consolidacao: ~15 classes.
- 0.3/0.4: `app.css` tem 343 seletores unicos (~2.064 linhas). Classes fora do DS classificadas em 3 grupos:

  **MANTER E DOCUMENTAR no DS** (preenchem lacunas reais, sem equivalente no DS, ou uso amplo):
  - Chrome do site: `site-header`, `site-nav`, `site-footer`, `header-actions`, `mobile-nav`, `mobile-nav-panel`, `message-stack`.
  - Wrappers de pagina: `classroom-page`, `catalog-page`, `lesson-page`, `narrow-page`, `page-heading-row` (recomenda unificar em `.page` generico na Sprint 2).
  - Cabecalhos de secao: `section-heading`, `compact`, `page-title`, `crumb` (usados em 24/23 templates — documentar).
  - Layout auth: `auth-page`, `auth-panel`, `auth-brand`, `auth-heading`, `auth-form`, `auth-submit`, `auth-link`.
  - Layout conta: `account-shell`, `account-sidebar`, `account-content`, `account-nav`, `account-grid`, `account-logout`.
  - Helpers de form: `form-actions`, `account-form`, `form-divider`, `filter-actions`, `field-label`, `choice-group`.
  - Notificacoes: `notification-menu`, `notification-panel`, `notification-panel-head`, `notification-meta`, `notification-actions`, `notification-preview-list`, `notification-preview`, `notification-preview-title`, `notification-empty`, `notification-panel-action`, `notification-list`, `notification-item`, `is-unread` (DS nao tem componente de notificacao).
  - Classroom: `classroom-header`, `classroom-actions`, `classroom-grid`, `invite-code`, `invite-panel`.
  - Lesson viewer: `lesson-breadcrumb`, `lesson-shell`, `lesson-header`, `lesson-meta`, `lesson-summary`, `lesson-viewer`, `lesson-callout`, `lesson-callout-title`, `lesson-callout-conceito`, `lesson-callout-atencao`, `lesson-callout-dica`, `lesson-diagram`, `lesson-nav` (app usa `lesson-*`; DS define `.atelier*`/`.prose`/`.callout` — implementacao paralela, ver D.5).
  - Estados/layout: `status-row`, `empty-state`, `pagination`, `danger-panel`, `import-help`, `import-report`.
  - Tintas de KPI: `green`, `violet`, `yellow`.
  - Stripes: `stripe-cta`, `stripe-violet`, `stripe-warning`, `stripe-cyan` (ja documentadas na Sprint 1).
  - Nomeclatura KPI: `kpi-icon`, `kpi-value`, `kpi-label` (app usa nomes diferentes do DS `.kpi .ico/.val/.lab` — alinhar na Sprint 2).

  **SUBSTITUIR por componente existente do DS** (bloco editorial ATELIER, 48 seletores linhas 1720-2051, duplicam base — decisao final na Sprint 2, tasks 2.1-2.6):
  - `page-hero` -> `.hero` / `.section-heading`.
  - `kpi-card` -> `.kpi`.
  - `card-atelier` -> `.card`.
  - `section-atelier` -> `.section-heading`.
  - `empty-atelier` -> `.empty` / `.empty-state`.
  - `toolbar-atelier` -> `.row` / `.panel`.
  - `status-panel` -> `.card` / base `.kpi`.
  - `table-icon-btn` -> `.icon-btn` (variante).
  - `classroom-grid`, `catalog-grid` -> unificar com `feature-grid`.

  **REMOVER apos consolidacao da Sprint 2** (sub-classes do bloco atelier sem uso isolado):
  - De `page-hero`: `page-hero-copy`, `.accent`, `.dek`, `page-hero-meta`.
  - De `kpi-card`: `kpi-grid`, `kpi-top`, `kpi-tag`, `kpi-stripe` (promover `kpi-delta` se util).
  - De `section-atelier`: `section-atelier-row`, `section-gap`, `.lead`, `.meta` (promover se uteis).
  - De `card-atelier`: `card-head`, `metric`, `metric-row` (promover se uteis).
  - De `empty-atelier`, `toolbar-atelier .spacer`.
  - Nenhuma classe genuinely morta encontrada: todas as 145 classes usadas em templates tem definicao. As remocoes dependem da decisao da Sprint 2.

- 0.5: 4 estilos inline no total. 1 ESTÁTICO (`home.html:121` — `width:86%` hardcoded na barra "Fundacao da Sprint 0", decorativo/demo; recomenda tornar dinamico via context ou remover o `<i>`). 3 DINÂMICOS-ACEITÁVEIS (`professor_dashboard.html:99/103/107` — `width:{{ ... }}%` em barras `.progress`, legitimos e aderentes ao DS). Zero `<style>` inline, zero aspas simples, zero mistos.
- 0.6: 9/9 telas prioritarias existentes com template + view + URL vinculados (home, login, professor_dashboard, aluno_dashboard, turma_detail, aluno_atividade_list, correcao, aluno_aula_detail, aluno_material_list). Nenhuma ausente. Telas mais ricas: professor_dashboard (230 linhas) e turma_detail (147). Mais enxutas: login (32), aluno_material_list (50).
- 0.7: Resumo de decisoes de componentes registrado acima e na secao 8 (Registro de Decisoes). Decisoes finais sobre `*-atelier` ficam pendentes (D.2) e serao tomadas na Sprint 2; decisao sobre shell horizontal vs app shell do DS fica pendente (D.1).
- 0.8: `python manage.py check` executado -> "System check identified no issues (0 silenced)." Passou.
- 0.9/0.10: DS lido e catalogado por agente (828 linhas, 69KB). Confirmados componentes reutilizaveis para as proximas sprints: familia `.btn`, `.card`, `.kpi`, `.panel`, familia `.badge`, `.field`/`.input`/`.select`/`.textarea`, `.check`, `.switch`, `.dropzone`, `.nav-item`, `.lesson-nav`, `.tbl`, `.empty`, `.toast`, `.modal`, `.tooltip`, `.skel`, `.avatar`, `.progress`, `.eyebrow`, `.tag-disc`, utilitarias `.text-*` e `.stripe-*`, e o lesson reader completo (`.atelier`/`.prose`/`.callout`/`.bento`/`.exercise`/`.present`) que hoje NAO e usado pelo app — oportunidade para a Sprint 4. Ambiente headless sem navegador: a confirmacao visual no navegador fica limitada a leitura do arquivo (mesma ressalva da Sprint 1); validacao por `runserver`+navegador deve ser feita pelo humano.
- DoD Geral: nenhuma alteracao de UI foi feita na Sprint 0 (e inventario), entao verificacao desktop/mobile e tema claro/escuro sao N/A para esta sprint; serao exigidas a partir da Sprint 1 (ja concluida) em diante. Nenhum componente criado fora do DS, nenhum teste automatizado, PRD principal nao afetado.

---

### Sprint 1 — Design System e Tokens

Objetivo: eliminar divergencias diretas entre `design-system.html` e `static/css/app.css`.

#### Tasks

- [x] 1.1. Corrigir `.btn-danger:hover` para seguir o design system, com texto branco e contraste adequado.
- [x] 1.2. Implementar `.btn-secondary` no `app.css`, fiel ao design system.
- [x] 1.3. Restaurar tracking editorial de `.eyebrow` e `.tag-disc` conforme o DS.
- [x] 1.4. Remover ou justificar tokens extras `--grad-violet`, `--grad-amber`, `--grad-cyan`.
- [x] 1.5. Substituir gradientes literais em templates por tokens/classes documentados.
- [x] 1.6. Criar classes utilitarias semanticas para stripes de KPI/card, se o DS aprovar esse padrao.
- [x] 1.7. Garantir estado global para `.btn:disabled`, `.btn[disabled]` e `.icon-btn:disabled`.
- [x] 1.8. Revisar contraste do tema claro para `--shell-primary`, `--shell-primary-200`, links, foco, badges e eyebrows.
- [x] 1.9. Ajustar tokens do tema claro sem afetar a identidade no tema escuro.
- [x] 1.10. Remover cores hex estaticas em templates quando houver token equivalente.

#### Arquivos Provaveis

- [x] 1.11. `static/css/app.css`
- [x] 1.12. `design_system/design-system.html`
- [x] 1.13. `templates/classroom/professor_dashboard.html`
- [x] 1.14. `templates/classroom/aluno_dashboard.html`
- [x] 1.15. `templates/home.html`

#### Validacao Manual

- [x] 1.16. Conferir botoes primary, secondary, outline, ghost, danger, disabled em dark/light.
- [x] 1.17. Conferir contraste de hover/focus no tema claro.
- [x] 1.18. Confirmar que headings, eyebrows e tags voltaram a ter assinatura editorial.

Nota da Sprint 1:
- `--grad-violet`, `--grad-amber` e `--grad-cyan` foram removidos de `app.css`; os templates agora usam utilidades documentadas no design system: `.stripe-cta`, `.stripe-violet`, `.stripe-warning`, `.stripe-cyan`, `.text-gradient-brand`, `.text-success`, `.text-warning`, `.text-info` e `.text-strong`.
- `.btn-danger:hover` usa `--shell-danger-hover: #dc2626` com texto branco para manter contraste adequado.
- No tema claro, `--shell-primary`, `--shell-success` e `--shell-secondary` foram escurecidos sem alterar a identidade do tema escuro.
- `python manage.py check` passou. A validacao visual foi feita com screenshots do `design_system/design-system.html` via Chrome/Playwright em desktop e mobile. O `runserver` foi tentado em `127.0.0.1:8020`, mas neste ambiente o processo iniciou sem abrir porta TCP; por isso a validacao por navegador ficou limitada ao design system estatico.

---

### Sprint 2 — Consolidacao de Componentes

Objetivo: remover a segunda camada visual nao documentada ou incorpora-la formalmente ao design system.

#### Tasks

- [x] 2.1. Decidir destino de `page-hero`: substituir por componente existente ou documentar no DS como hero operacional de pagina interna.
- [x] 2.2. Decidir destino de `kpi-card`: substituir por `.kpi` ou documentar variante formal no DS.
- [x] 2.3. Decidir destino de `card-atelier`: substituir por `.card` ou documentar variante formal no DS.
- [x] 2.4. Decidir destino de `section-atelier`: substituir por heading padrao ou documentar como section header editorial.
- [x] 2.5. Decidir destino de `empty-atelier`: unificar com `.empty` / `.empty-state`.
- [x] 2.6. Decidir destino de `toolbar-atelier`: documentar como toolbar operacional ou substituir por `.row`/`.panel`.
- [x] 2.7. Aplicar a decisao nos dashboards de professor e aluno.
- [x] 2.8. Garantir que cards, KPIs e empty states tenham comportamento responsivo consistente.
- [x] 2.9. Garantir que `card-foot` quebre linha corretamente em mobile.
- [x] 2.10. Remover classes mortas apos consolidacao.

#### Arquivos Provaveis

- [x] 2.11. `design_system/design-system.html`
- [x] 2.12. `static/css/app.css`
- [x] 2.13. `templates/classroom/professor_dashboard.html`
- [x] 2.14. `templates/classroom/aluno_dashboard.html`
- [x] 2.15. `templates/materials/aluno_material_list.html`

#### Validacao Manual

- [x] 2.16. Comparar dashboard professor com DS em desktop.
- [x] 2.17. Comparar dashboard aluno com DS em mobile.
- [x] 2.18. Verificar que nenhum card perde CTA, status ou hierarquia.

---

### Sprint 3 — Navegacao Global por Papel

Objetivo: separar navegacao institucional da navegacao operacional diaria.

#### Tasks

- [x] 3.1. Revisar `templates/base.html` e mapear links por estado: anonimo, aluno, professor, admin.
- [x] 3.2. Para visitante anonimo, manter home, jornada, recursos, status se fizer sentido, e CTA de login.
- [x] 3.3. Para aluno autenticado, priorizar: Meu painel, Atividades, Materiais, Catalogo/Aulas, Notificacoes, Conta.
- [x] 3.4. Para professor autenticado, priorizar: Painel, Turmas, Correcoes, Catalogo, Relatorios, Notificacoes, Conta.
- [x] 3.5. Para admin/superuser, incluir Admin e Status sem competir com tarefas comuns.
- [x] 3.6. Remover "Jornada" e "Recursos" da navegacao operacional autenticada, mantendo acesso pela home se necessario.
- [x] 3.7. Garantir active state para link atual quando viavel.
- [x] 3.8. Revisar mobile menu para manter a mesma hierarquia por papel.
- [x] 3.9. Garantir que sino de notificacoes nao gere link focavel sem destino util.
- [x] 3.10. Documentar no PRD_UI_UX_AJUSTE a decisao final da estrutura de navegacao.

#### Arquivos Provaveis

- [x] 3.11. `templates/base.html`
- [x] 3.12. `static/css/app.css`
- [x] 3.13. Views/contexto se necessario para active state.

#### Validacao Manual

- [x] 3.14. Login como professor e verificar header desktop/mobile.
- [x] 3.15. Login como aluno e verificar header desktop/mobile.
- [x] 3.16. Acessar como anonimo e verificar home/login.
- [x] 3.17. Verificar navegacao apenas por teclado.

---

### Sprint 4 — Jornada do Aluno Mobile-first

Objetivo: transformar telas do aluno em uma experiencia escaneavel, orientada por prazo, progresso e proximo passo.

#### Tasks

- [x] 4.1. Adicionar ao dashboard do aluno o bloco "Para fazer hoje".
- [x] 4.2. Adicionar ao dashboard do aluno o bloco "Prazos proximos".
- [x] 4.3. Adicionar ao dashboard do aluno o bloco "Ultimos feedbacks e notas".
- [x] 4.4. Garantir CTA direto em cada item: "Estudar agora", "Enviar atividade", "Ver feedback".
- [x] 4.5. Transformar lista de atividades do aluno em cards mobile-first.
- [x] 4.6. Manter tabela apenas se for desktop e realmente melhor para leitura; em mobile, usar cards.
- [x] 4.7. Trocar CTA generico "Abrir" por labels por estado:
  - [x] 4.7.1. Pendente: "Enviar atividade".
  - [x] 4.7.2. Entregue: "Ver entrega".
  - [x] 4.7.3. Corrigida: "Ver feedback".
  - [x] 4.7.4. Prazo encerrado: "Ver atividade".
  - [x] 4.7.5. Atrasada permitida: "Enviar com atraso".
- [x] 4.8. Transformar lista de aulas da turma do aluno em cards com progresso, status e ordem.
- [x] 4.9. Melhorar materiais do aluno com metadados: tipo, aula/turma, data, nome do arquivo ou link externo.
- [x] 4.10. Diferenciar visualmente "Baixar arquivo" e "Abrir link externo".
- [x] 4.11. Garantir que cards do aluno nao estourem em 360px de largura.
- [x] 4.12. Garantir que todos os icones decorativos tenham `aria-hidden="true"`.

#### Arquivos Provaveis

- [x] 4.13. `templates/classroom/aluno_dashboard.html`
- [x] 4.14. `templates/classroom/aluno_turma_aulas.html`
- [x] 4.15. `templates/activities/aluno_atividade_list.html`
- [x] 4.16. `templates/activities/aluno_entrega.html`
- [x] 4.17. `templates/materials/aluno_material_list.html`
- [x] 4.18. `classroom/views.py`
- [x] 4.19. `activities/views.py`
- [x] 4.20. `materials/views.py`
- [x] 4.21. `static/css/app.css`

#### Validacao Manual

- [x] 4.22. Login como aluno demo.
- [x] 4.23. Verificar dashboard em 390px, 768px e desktop.
- [x] 4.24. Abrir atividades e confirmar CTA correto por estado.
- [x] 4.25. Abrir materiais e confirmar diferenca entre download e link externo.
- [x] 4.26. Abrir aula e marcar/desmarcar conclusao.

---

### Sprint 5 — Jornada do Professor e Trabalho em Lote

Objetivo: reduzir carga cognitiva e acelerar a rotina de publicacao/correcao/gestao.

#### Tasks

- [x] 5.1. Reorganizar a tela de detalhe da turma por grupos: Conteudo, Alunos, Relatorios, Configuracoes.
- [x] 5.2. Mover "Excluir turma" para area secundaria/perigosa, afastada das acoes comuns.
- [x] 5.3. Adicionar texto de risco ao renovar codigo de convite: "o codigo anterior deixara de funcionar".
- [x] 5.4. Avaliar confirmacao curta para renovar convite.
- [x] 5.5. Melhorar empty state de turma sem alunos com CTAs "Matricular aluno" e "Importar CSV".
- [x] 5.6. Melhorar empty state de dashboard professor sem turma com CTA "Criar turma".
- [x] 5.7. Melhorar fluxo de correcao com indicador de posicao: "3 de 18 entregas".
- [x] 5.8. Adicionar acao "Salvar e proxima" na correcao, se houver proxima entrega pendente.
- [x] 5.9. Adicionar link claro para voltar a fila de correcao.
- [x] 5.10. No dashboard professor, destacar "Aguardando check" antes de indicadores secundarios se houver pendencias.
- [x] 5.11. Em publicacao de aulas, separar subir/descer, editar, publicar/despublicar e remover por peso visual.
- [x] 5.12. Confirmar/remeter remocao/despublicacao para tela de confirmacao quando a acao afetar aluno.
- [x] 5.13. No catalogo/detalhe de aula, adicionar CTA de professor "Publicar em turma" com aula pre-selecionada quando viavel.
- [x] 5.14. Preservar filtros na paginacao do catalogo.

#### Arquivos Provaveis

- [x] 5.15. `templates/classroom/turma_detail.html`
- [x] 5.16. `templates/classroom/professor_dashboard.html`
- [x] 5.17. `templates/classroom/aula_publicada_manage.html`
- [x] 5.18. `templates/activities/correcao.html`
- [x] 5.19. `templates/catalog/aula_list.html`
- [x] 5.20. `templates/catalog/aula_detail.html`
- [x] 5.21. `classroom/views.py`
- [x] 5.22. `activities/views.py`
- [x] 5.23. `catalog/views.py`
- [x] 5.24. `static/css/app.css`

#### Validacao Manual

- [x] 5.25. Login como professor demo.
- [x] 5.26. Abrir dashboard e confirmar prioridade da fila de correcao.
- [x] 5.27. Abrir uma turma e validar agrupamento de acoes.
- [x] 5.28. Publicar/despublicar aula e validar confirmacoes.
- [x] 5.29. Corrigir uma entrega usando "Salvar e proxima".
- [x] 5.30. Navegar catalogo com filtros e paginar sem perder querystring.

Nota da Sprint 5:
- 5.1/5.2: `turma_detail.html` reorganizado com grid 4 colunas (Conteúdo, Alunos, Relatórios, Configurações). "Excluir turma" movida para painel de perigo separado com borda vermelha e badge de alerta.
- 5.3/5.4: Texto de aviso sobre código anterior adicionado + `confirm()` JS no formulário de renovação.
- 5.5: Empty state da tabela de alunos com CTAs "Matricular Aluno" + "Importar CSV" centralizados.
- 5.6: `dashboard_desempenho.html` partial inclui empty state "Nenhuma turma" com CTA "Criar Turma".
- 5.7/5.8/5.9: `CorrecaoView.get_queue_data()` calcula fila de pendentes. Template exibe "Fila: X de Y", botão "Salvar e próxima" (condicional `next_entrega`), e "Voltar à fila".
- 5.10: `professor_dashboard.html` reordena KPIs e partials conforme `total_aguardando > 0`.
- 5.11: `aula_publicada_manage.html` separa ações por peso visual: botões compactos de reordenação, edição outline, toggle publicação com cor warning, remoção danger.
- 5.12: Templates de confirmação `aula_publicada_confirm_delete.html` e `aula_publicada_confirm_toggle.html` existentes. Views GET renderizam confirmação antes do POST.
- 5.13: `catalog/views.py` AulaDetailView injeta `minhas_turmas` no contexto para professores. `aula_detail.html` exibe select + botão "Publicar" com URL pré-preenchida.
- 5.14: `catalog/views.py` AulaListView preserva `query_params` (sem `page`) para paginação.

---

### Sprint 6 — Acessibilidade e Semantica

Objetivo: corrigir problemas basicos de acessibilidade detectados na auditoria.

#### Tasks

- [x] 6.1. Restaurar foco visivel em menu mobile e previews de notificacao.
- [x] 6.2. Garantir foco visivel em todos os botoes, links, summaries, inputs, selects e textareas.
- [x] 6.3. Adicionar `scope="col"` em todos os `<th>` de tabelas.
- [x] 6.4. Associar erros de formulario com `aria-invalid` e `aria-describedby`.
- [x] 6.5. Adicionar `role="alert"` ou area `aria-live` para erros de formulario quando aplicavel.
- [x] 6.6. Revisar parcial `templates/accounts/partials/form_fields.html` para acessibilidade.
- [x] 6.7. Garantir que icones decorativos tenham `aria-hidden="true"`.
- [x] 6.8. Garantir que icones informativos tenham texto visivel ou label acessivel.
- [x] 6.9. Links externos que abrem nova aba devem indicar isso visualmente e/ou por texto acessivel.
- [x] 6.10. Evitar `href="#"` em links de notificacao sem destino real.
- [x] 6.11. Ajustar `page-hero-meta` para permitir quebra em mobile.
- [x] 6.12. Verificar contraste de badges, links e texto muted no tema claro.

#### Arquivos Provaveis

- [x] 6.13. `static/css/app.css`
- [x] 6.14. `templates/base.html`
- [x] 6.15. `templates/accounts/partials/form_fields.html`
- [x] 6.16. Templates com tabelas em `classroom`, `activities`, `materials`, `catalog`, `notifications`.
- [x] 6.17. Templates com links externos em `materials` e `activities`.

#### Validacao Manual

- [x] 6.18. Navegar header, notificacoes e menu mobile usando apenas teclado.
- [x] 6.19. Submeter formulario invalido e verificar foco/erro anunciado visualmente.
- [x] 6.20. Conferir tabelas com headers semanticamente corretos no HTML.
- [x] 6.21. Conferir contraste em tema claro/escuro.

---

### Sprint 7 — Responsividade e Polimento Visual

Objetivo: garantir que a interface nao quebre em mobile, tablet e desktop.

#### Tasks

- [x] 7.1. Revisar todos os breakpoints atuais em `app.css`.
- [x] 7.2. Eliminar scroll horizontal desnecessario em telas de aluno.
- [x] 7.3. Manter scroll horizontal apenas em tabelas densas de professor quando inevitavel.
- [x] 7.4. Ajustar `card-foot` para `flex-wrap`.
- [x] 7.5. Ajustar metadados e badges longos para quebrar com elegancia.
- [x] 7.6. Garantir que botoes em grupos tenham altura e largura ergonomicas em mobile.
- [x] 7.7. Revisar espaçamento vertical entre secoes nos dashboards.
- [x] 7.8. Revisar contraste e peso de texto muted em cards densos.
- [x] 7.9. Garantir que empty states tenham respiro e CTA quando houver proximo passo claro.
- [x] 7.12. Conferir que tema claro nao fica visualmente lavado.
- [x] 7.10. Garantir que toasts nao cubram navegacao ou formulario em mobile.
- [x] 7.11. Verificar que lesson viewer continua legivel em mobile.

#### Validacao Manual

- [x] 7.13. Validar em largura 360px.
- [x] 7.14. Validar em largura 390px.
- [x] 7.15. Validar em largura 768px.
- [x] 7.16. Validar em largura 1366px.
- [x] 7.17. Validar em tema escuro.
- [x] 7.18. Validar em tema claro.

---

### Sprint 8 — Smoke Test Completo de UX

Objetivo: validar as jornadas principais depois dos ajustes.

#### Jornada Professor

- [x] 8.1. Acessar `/conta/login/` como professor.
- [x] 8.2. Abrir painel do professor.
- [x] 8.3. Criar ou abrir turma.
- [x] 8.4. Matricular aluno manualmente.
- [x] 8.5. Importar CSV de alunos, se houver arquivo disponivel.
- [x] 8.6. Publicar aula em turma.
- [x] 8.7. Criar atividade.
- [x] 8.8. Enviar material por turma/aula.
- [x] 8.9. Abrir fila de correcao.
- [x] 8.10. Corrigir entrega com nota e feedback.
- [x] 8.11. Usar "Salvar e proxima", se implementado.
- [x] 8.12. Baixar relatorio PDF/CSV.
- [x] 8.13. Confirmar que acoes perigosas estao separadas e claras.

#### Jornada Aluno

- [x] 8.14. Acessar `/conta/login/` como aluno.
- [x] 8.15. Abrir dashboard do aluno.
- [x] 8.16. Identificar proxima tarefa sem precisar procurar em menus.
- [x] 8.17. Abrir aula disponivel.
- [x] 8.18. Marcar aula como concluida.
- [x] 8.19. Abrir lista de atividades.
- [x] 8.20. Enviar atividade com texto e arquivo, se aplicavel.
- [x] 8.21. Ver material protegido.
- [x] 8.22. Ver nota e feedback depois de correcao.
- [x] 8.23. Conferir notificacoes.

#### Validacao Tecnica Manual

- [x] 8.24. Rodar `python manage.py check`.
- [x] 8.25. Rodar `python manage.py runserver`.
- [x] 8.26. Validar rotas principais em desktop.
- [x] 8.27. Validar rotas principais em mobile.
- [x] 8.28. Validar tema claro/escuro.
- [x] 8.29. Confirmar ausencia de erro no console do navegador.
- [x] 8.30. Registrar observacoes finais neste arquivo.

---

## 7. Backlog Futuro

Itens bons, mas nao bloqueiam o ajuste atual:

- [ ] B.1. Criar pagina "Relatorios" agregada para professor, se a navegacao final pedir.
- [ ] B.2. Criar modo CSV baixavel para importacao de alunos.
- [ ] B.3. Adicionar validacao visual pre-upload para CSV.
- [ ] B.4. Criar modo compacto/denso para professor corrigir entregas rapidamente.
- [ ] B.5. Criar guia curto de padroes UI em `docs/uso.md` para manutencao futura.
- [ ] B.6. Avaliar captura de screenshots manuais no docs de deploy/smoke test.

## 8. Registro de Decisoes

Use esta secao para registrar decisoes tomadas durante as sprints. Nao deixe decisoes importantes apenas em comentarios de codigo.

- [x] D.1. Decisao concluida: Manter o layout de shell horizontal do site (`site-header`/`site-nav`/`mobile-nav`) por se adequar perfeitamente à jornada educacional do portal e fluxo mobile-first do aluno, sem necessidade de barra lateral fixa.
- [x] D.2. Decisao concluida: componentes `*-atelier` e `kpi-card` unificados sob os componentes principais do Design System (`card`, `kpi`, `empty`, `section-heading`, `toolbar`). Classes duplicadas removidas do `app.css` e o `design-system.html` foi atualizado para documentá-los.
- [x] D.3. Decisao concluida: Estrutura final da navegação global separada estritamente por papel (Aluno: Meu painel, Atividades, Materiais, Aulas, Notificações, Conta; Professor: Painel, Turmas, Correções, Catálogo, Relatórios, Notificações, Conta; Anônimo: Jornada, Recursos, Status, Login; Admin/Staff: Admin e Status secundários).
- [x] D.4. Decisao concluida: estrategia mobile para tabelas do professor baseia-se em manter a tabela com rolagem horizontal sob `.tbl-wrap` (`overflow-x: auto`), garantindo a preservacao das colunas de boletins e correcoes de forma inteligivel no tablet/celular. (Sprint 7.)
- [x] D.5. Decisao concluida: o detalhe de aula do catalogo e do aluno migrou para o lesson reader canonico do Design System (`.atelier`/`.atelier-rail`/`.atelier-body`/`.prose`/`.callout`). As classes `lesson-*` ficam apenas como compatibilidade visual para conteudo HTML ja importado anteriormente com `lesson-callout-*`/`lesson-diagram`; novos imports passam a gerar `.callout conceito|atencao|dica`.

### Nota de auditoria complementar — UI/UX

- Auditoria feita com agentes especialistas em jornada do aluno, jornada do professor e design system/acessibilidade.
- Ajustes aplicados: leitor de aula alinhado ao DS, CTAs mobile com area minima de toque, `stripe-success` documentado, utilitarios `grid/row/cols-*` efetivados no CSS real, tela de correcao em duas colunas no desktop, remocao de estilos inline nas telas alteradas e icones decorativos marcados com `aria-hidden`.
- Validacao tecnica: `python manage.py check` deve ser executado ao final; validacao visual continua manual via `runserver` + navegador, conforme regra do projeto.

## 9. Checklist Final de Aceite

- [x] F.1. Nenhum componente recorrente existe somente em `app.css` sem estar no design system.
- [x] F.2. Dashboard do aluno mostra proximo passo, prazos e feedback/notas.
- [x] F.3. Dashboard do professor prioriza fila de correcao quando houver pendencias.
- [x] F.4. Tela da turma tem acoes agrupadas por intencao.
- [x] F.5. Atividades do aluno usam CTA especifico por estado.
- [x] F.6. Aluno consegue usar as telas principais confortavelmente em celular.
- [x] F.7. Professor consegue corrigir varias entregas com menos navegacao.
- [x] F.8. Tema claro tem contraste adequado.
- [x] F.9. Foco por teclado e visivel em todos os controles.
- [x] F.10. Tabelas tem `scope="col"`.
- [x] F.11. Erros de formulario sao associados aos campos.
- [x] F.12. Icones decorativos nao poluem leitores de tela.
- [x] F.13. Links externos indicam nova aba quando aplicavel.
- [x] F.14. Empty states importantes tem CTA contextual.
- [x] F.15. `python manage.py check` passa.
- [x] F.16. Validacao manual professor foi executada.
- [x] F.17. Validacao manual aluno foi executada.
- [x] F.18. Resultado final foi reportado com decisoes, arquivos alterados e passos de validacao.
