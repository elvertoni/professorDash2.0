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

- [ ] 0.1. Reler `AGENTS.md`, `PRD_PROF_DASH.md`, `CLAUDE.md` e `design_system/design-system.html`.
- [ ] 0.2. Mapear todos os componentes CSS usados em templates com `rg -n "class=\"" templates static/css/app.css`.
- [ ] 0.3. Listar classes presentes em `app.css` que nao existem no design system.
- [ ] 0.4. Classificar classes extras em tres grupos: manter e documentar, substituir por componente existente, remover.
- [ ] 0.5. Identificar todos os estilos inline estaticos em templates, separando os dinamicos aceitaveis como `width:{{ pct }}%`.
- [ ] 0.6. Identificar telas prioritarias para validacao manual: home, login, dashboard professor, dashboard aluno, detalhe turma, lista atividades aluno, correcao, aula aluno, materiais aluno.
- [ ] 0.7. Registrar no final desta sprint um resumo curto das decisoes de componentes.

#### Validacao Manual

- [ ] 0.8. Rodar `python manage.py check`.
- [ ] 0.9. Abrir o design system local no navegador.
- [ ] 0.10. Confirmar visualmente quais componentes do DS devem ser reaproveitados.

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

- [ ] 2.1. Decidir destino de `page-hero`: substituir por componente existente ou documentar no DS como hero operacional de pagina interna.
- [ ] 2.2. Decidir destino de `kpi-card`: substituir por `.kpi` ou documentar variante formal no DS.
- [ ] 2.3. Decidir destino de `card-atelier`: substituir por `.card` ou documentar variante formal no DS.
- [ ] 2.4. Decidir destino de `section-atelier`: substituir por heading padrao ou documentar como section header editorial.
- [ ] 2.5. Decidir destino de `empty-atelier`: unificar com `.empty` / `.empty-state`.
- [ ] 2.6. Decidir destino de `toolbar-atelier`: documentar como toolbar operacional ou substituir por `.row`/`.panel`.
- [ ] 2.7. Aplicar a decisao nos dashboards de professor e aluno.
- [ ] 2.8. Garantir que cards, KPIs e empty states tenham comportamento responsivo consistente.
- [ ] 2.9. Garantir que `card-foot` quebre linha corretamente em mobile.
- [ ] 2.10. Remover classes mortas apos consolidacao.

#### Arquivos Provaveis

- [ ] 2.11. `design_system/design-system.html`
- [ ] 2.12. `static/css/app.css`
- [ ] 2.13. `templates/classroom/professor_dashboard.html`
- [ ] 2.14. `templates/classroom/aluno_dashboard.html`
- [ ] 2.15. `templates/materials/aluno_material_list.html`

#### Validacao Manual

- [ ] 2.16. Comparar dashboard professor com DS em desktop.
- [ ] 2.17. Comparar dashboard aluno com DS em mobile.
- [ ] 2.18. Verificar que nenhum card perde CTA, status ou hierarquia.

---

### Sprint 3 — Navegacao Global por Papel

Objetivo: separar navegacao institucional da navegacao operacional diaria.

#### Tasks

- [ ] 3.1. Revisar `templates/base.html` e mapear links por estado: anonimo, aluno, professor, admin.
- [ ] 3.2. Para visitante anonimo, manter home, jornada, recursos, status se fizer sentido, e CTA de login.
- [ ] 3.3. Para aluno autenticado, priorizar: Meu painel, Atividades, Materiais, Catalogo/Aulas, Notificacoes, Conta.
- [ ] 3.4. Para professor autenticado, priorizar: Painel, Turmas, Correcoes, Catalogo, Relatorios, Notificacoes, Conta.
- [ ] 3.5. Para admin/superuser, incluir Admin e Status sem competir com tarefas comuns.
- [ ] 3.6. Remover "Jornada" e "Recursos" da navegacao operacional autenticada, mantendo acesso pela home se necessario.
- [ ] 3.7. Garantir active state para link atual quando viavel.
- [ ] 3.8. Revisar mobile menu para manter a mesma hierarquia por papel.
- [ ] 3.9. Garantir que sino de notificacoes nao gere link focavel sem destino util.
- [ ] 3.10. Documentar no PRD_UI_UX_AJUSTE a decisao final da estrutura de navegacao.

#### Arquivos Provaveis

- [ ] 3.11. `templates/base.html`
- [ ] 3.12. `static/css/app.css`
- [ ] 3.13. Views/contexto se necessario para active state.

#### Validacao Manual

- [ ] 3.14. Login como professor e verificar header desktop/mobile.
- [ ] 3.15. Login como aluno e verificar header desktop/mobile.
- [ ] 3.16. Acessar como anonimo e verificar home/login.
- [ ] 3.17. Verificar navegacao apenas por teclado.

---

### Sprint 4 — Jornada do Aluno Mobile-first

Objetivo: transformar telas do aluno em uma experiencia escaneavel, orientada por prazo, progresso e proximo passo.

#### Tasks

- [ ] 4.1. Adicionar ao dashboard do aluno o bloco "Para fazer hoje".
- [ ] 4.2. Adicionar ao dashboard do aluno o bloco "Prazos proximos".
- [ ] 4.3. Adicionar ao dashboard do aluno o bloco "Ultimos feedbacks e notas".
- [ ] 4.4. Garantir CTA direto em cada item: "Estudar agora", "Enviar atividade", "Ver feedback".
- [ ] 4.5. Transformar lista de atividades do aluno em cards mobile-first.
- [ ] 4.6. Manter tabela apenas se for desktop e realmente melhor para leitura; em mobile, usar cards.
- [ ] 4.7. Trocar CTA generico "Abrir" por labels por estado:
  - [ ] 4.7.1. Pendente: "Enviar atividade".
  - [ ] 4.7.2. Entregue: "Ver entrega".
  - [ ] 4.7.3. Corrigida: "Ver feedback".
  - [ ] 4.7.4. Prazo encerrado: "Ver atividade".
  - [ ] 4.7.5. Atrasada permitida: "Enviar com atraso".
- [ ] 4.8. Transformar lista de aulas da turma do aluno em cards com progresso, status e ordem.
- [ ] 4.9. Melhorar materiais do aluno com metadados: tipo, aula/turma, data, nome do arquivo ou link externo.
- [ ] 4.10. Diferenciar visualmente "Baixar arquivo" e "Abrir link externo".
- [ ] 4.11. Garantir que cards do aluno nao estourem em 360px de largura.
- [ ] 4.12. Garantir que todos os icones decorativos tenham `aria-hidden="true"`.

#### Arquivos Provaveis

- [ ] 4.13. `templates/classroom/aluno_dashboard.html`
- [ ] 4.14. `templates/classroom/aluno_turma_aulas.html`
- [ ] 4.15. `templates/activities/aluno_atividade_list.html`
- [ ] 4.16. `templates/activities/aluno_entrega.html`
- [ ] 4.17. `templates/materials/aluno_material_list.html`
- [ ] 4.18. `classroom/views.py`
- [ ] 4.19. `activities/views.py`
- [ ] 4.20. `materials/views.py`
- [ ] 4.21. `static/css/app.css`

#### Validacao Manual

- [ ] 4.22. Login como aluno demo.
- [ ] 4.23. Verificar dashboard em 390px, 768px e desktop.
- [ ] 4.24. Abrir atividades e confirmar CTA correto por estado.
- [ ] 4.25. Abrir materiais e confirmar diferenca entre download e link externo.
- [ ] 4.26. Abrir aula e marcar/desmarcar conclusao.

---

### Sprint 5 — Jornada do Professor e Trabalho em Lote

Objetivo: reduzir carga cognitiva e acelerar a rotina de publicacao/correcao/gestao.

#### Tasks

- [ ] 5.1. Reorganizar a tela de detalhe da turma por grupos: Conteudo, Alunos, Relatorios, Configuracoes.
- [ ] 5.2. Mover "Excluir turma" para area secundaria/perigosa, afastada das acoes comuns.
- [ ] 5.3. Adicionar texto de risco ao renovar codigo de convite: "o codigo anterior deixara de funcionar".
- [ ] 5.4. Avaliar confirmacao curta para renovar convite.
- [ ] 5.5. Melhorar empty state de turma sem alunos com CTAs "Matricular aluno" e "Importar CSV".
- [ ] 5.6. Melhorar empty state de dashboard professor sem turma com CTA "Criar turma".
- [ ] 5.7. Melhorar fluxo de correcao com indicador de posicao: "3 de 18 entregas".
- [ ] 5.8. Adicionar acao "Salvar e proxima" na correcao, se houver proxima entrega pendente.
- [ ] 5.9. Adicionar link claro para voltar a fila de correcao.
- [ ] 5.10. No dashboard professor, destacar "Aguardando check" antes de indicadores secundarios se houver pendencias.
- [ ] 5.11. Em publicacao de aulas, separar subir/descer, editar, publicar/despublicar e remover por peso visual.
- [ ] 5.12. Confirmar/remeter remocao/despublicacao para tela de confirmacao quando a acao afetar aluno.
- [ ] 5.13. No catalogo/detalhe de aula, adicionar CTA de professor "Publicar em turma" com aula pre-selecionada quando viavel.
- [ ] 5.14. Preservar filtros na paginacao do catalogo.

#### Arquivos Provaveis

- [ ] 5.15. `templates/classroom/turma_detail.html`
- [ ] 5.16. `templates/classroom/professor_dashboard.html`
- [ ] 5.17. `templates/classroom/aula_publicada_manage.html`
- [ ] 5.18. `templates/activities/correcao.html`
- [ ] 5.19. `templates/catalog/aula_list.html`
- [ ] 5.20. `templates/catalog/aula_detail.html`
- [ ] 5.21. `classroom/views.py`
- [ ] 5.22. `activities/views.py`
- [ ] 5.23. `catalog/views.py`
- [ ] 5.24. `static/css/app.css`

#### Validacao Manual

- [ ] 5.25. Login como professor demo.
- [ ] 5.26. Abrir dashboard e confirmar prioridade da fila de correcao.
- [ ] 5.27. Abrir uma turma e validar agrupamento de acoes.
- [ ] 5.28. Publicar/despublicar aula e validar confirmacoes.
- [ ] 5.29. Corrigir uma entrega usando "Salvar e proxima".
- [ ] 5.30. Navegar catalogo com filtros e paginar sem perder querystring.

---

### Sprint 6 — Acessibilidade e Semantica

Objetivo: corrigir problemas basicos de acessibilidade detectados na auditoria.

#### Tasks

- [ ] 6.1. Restaurar foco visivel em menu mobile e previews de notificacao.
- [ ] 6.2. Garantir foco visivel em todos os botoes, links, summaries, inputs, selects e textareas.
- [ ] 6.3. Adicionar `scope="col"` em todos os `<th>` de tabelas.
- [ ] 6.4. Associar erros de formulario com `aria-invalid` e `aria-describedby`.
- [ ] 6.5. Adicionar `role="alert"` ou area `aria-live` para erros de formulario quando aplicavel.
- [ ] 6.6. Revisar parcial `templates/accounts/partials/form_fields.html` para acessibilidade.
- [ ] 6.7. Garantir que icones decorativos tenham `aria-hidden="true"`.
- [ ] 6.8. Garantir que icones informativos tenham texto visivel ou label acessivel.
- [ ] 6.9. Links externos que abrem nova aba devem indicar isso visualmente e/ou por texto acessivel.
- [ ] 6.10. Evitar `href="#"` em links de notificacao sem destino real.
- [ ] 6.11. Ajustar `page-hero-meta` para permitir quebra em mobile.
- [ ] 6.12. Verificar contraste de badges, links e texto muted no tema claro.

#### Arquivos Provaveis

- [ ] 6.13. `static/css/app.css`
- [ ] 6.14. `templates/base.html`
- [ ] 6.15. `templates/accounts/partials/form_fields.html`
- [ ] 6.16. Templates com tabelas em `classroom`, `activities`, `materials`, `catalog`, `notifications`.
- [ ] 6.17. Templates com links externos em `materials` e `activities`.

#### Validacao Manual

- [ ] 6.18. Navegar header, notificacoes e menu mobile usando apenas teclado.
- [ ] 6.19. Submeter formulario invalido e verificar foco/erro anunciado visualmente.
- [ ] 6.20. Conferir tabelas com headers semanticamente corretos no HTML.
- [ ] 6.21. Conferir contraste em tema claro/escuro.

---

### Sprint 7 — Responsividade e Polimento Visual

Objetivo: garantir que a interface nao quebre em mobile, tablet e desktop.

#### Tasks

- [ ] 7.1. Revisar todos os breakpoints atuais em `app.css`.
- [ ] 7.2. Eliminar scroll horizontal desnecessario em telas de aluno.
- [ ] 7.3. Manter scroll horizontal apenas em tabelas densas de professor quando inevitavel.
- [ ] 7.4. Ajustar `card-foot` para `flex-wrap`.
- [ ] 7.5. Ajustar metadados e badges longos para quebrar com elegancia.
- [ ] 7.6. Garantir que botoes em grupos tenham altura e largura ergonomicas em mobile.
- [ ] 7.7. Revisar espaçamento vertical entre secoes nos dashboards.
- [ ] 7.8. Revisar contraste e peso de texto muted em cards densos.
- [ ] 7.9. Garantir que empty states tenham respiro e CTA quando houver proximo passo claro.
- [ ] 7.10. Garantir que toasts nao cubram navegacao ou formulario em mobile.
- [ ] 7.11. Verificar que lesson viewer continua legivel em mobile.
- [ ] 7.12. Conferir que tema claro nao fica visualmente lavado.

#### Validacao Manual

- [ ] 7.13. Validar em largura 360px.
- [ ] 7.14. Validar em largura 390px.
- [ ] 7.15. Validar em largura 768px.
- [ ] 7.16. Validar em largura 1366px.
- [ ] 7.17. Validar em tema escuro.
- [ ] 7.18. Validar em tema claro.

---

### Sprint 8 — Smoke Test Completo de UX

Objetivo: validar as jornadas principais depois dos ajustes.

#### Jornada Professor

- [ ] 8.1. Acessar `/conta/login/` como professor.
- [ ] 8.2. Abrir painel do professor.
- [ ] 8.3. Criar ou abrir turma.
- [ ] 8.4. Matricular aluno manualmente.
- [ ] 8.5. Importar CSV de alunos, se houver arquivo disponivel.
- [ ] 8.6. Publicar aula em turma.
- [ ] 8.7. Criar atividade.
- [ ] 8.8. Enviar material por turma/aula.
- [ ] 8.9. Abrir fila de correcao.
- [ ] 8.10. Corrigir entrega com nota e feedback.
- [ ] 8.11. Usar "Salvar e proxima", se implementado.
- [ ] 8.12. Baixar relatorio PDF/CSV.
- [ ] 8.13. Confirmar que acoes perigosas estao separadas e claras.

#### Jornada Aluno

- [ ] 8.14. Acessar `/conta/login/` como aluno.
- [ ] 8.15. Abrir dashboard do aluno.
- [ ] 8.16. Identificar proxima tarefa sem precisar procurar em menus.
- [ ] 8.17. Abrir aula disponivel.
- [ ] 8.18. Marcar aula como concluida.
- [ ] 8.19. Abrir lista de atividades.
- [ ] 8.20. Enviar atividade com texto e arquivo, se aplicavel.
- [ ] 8.21. Ver material protegido.
- [ ] 8.22. Ver nota e feedback depois de correcao.
- [ ] 8.23. Conferir notificacoes.

#### Validacao Tecnica Manual

- [ ] 8.24. Rodar `python manage.py check`.
- [ ] 8.25. Rodar `python manage.py runserver`.
- [ ] 8.26. Validar rotas principais em desktop.
- [ ] 8.27. Validar rotas principais em mobile.
- [ ] 8.28. Validar tema claro/escuro.
- [ ] 8.29. Confirmar ausencia de erro no console do navegador.
- [ ] 8.30. Registrar observacoes finais neste arquivo.

---

## 7. Backlog Futuro

Itens bons, mas nao bloqueiam o ajuste atual:

- [ ] B.1. Criar pagina "Relatorios" agregada para professor, se a navegacao final pedir.
- [ ] B.2. Criar modelo CSV baixavel para importacao de alunos.
- [ ] B.3. Adicionar validacao visual pre-upload para CSV.
- [ ] B.4. Criar modo compacto/denso para professor corrigir entregas rapidamente.
- [ ] B.5. Criar guia curto de padroes UI em `docs/uso.md` para manutencao futura.
- [ ] B.6. Avaliar captura de screenshots manuais no docs de deploy/smoke test.

## 8. Registro de Decisoes

Use esta secao para registrar decisoes tomadas durante as sprints. Nao deixe decisoes importantes apenas em comentarios de codigo.

- [ ] D.1. Decisao pendente: manter shell horizontal atual ou migrar para app shell do design system.
- [ ] D.2. Decisao pendente: formalizar componentes `*-atelier` no design system ou substitui-los por componentes existentes.
- [ ] D.3. Decisao pendente: estrutura final da navegacao por papel.
- [ ] D.4. Decisao pendente: estrategia mobile para tabelas do professor.

## 9. Checklist Final de Aceite

- [ ] F.1. Nenhum componente recorrente existe somente em `app.css` sem estar no design system.
- [ ] F.2. Dashboard do aluno mostra proximo passo, prazos e feedback/notas.
- [ ] F.3. Dashboard do professor prioriza fila de correcao quando houver pendencias.
- [ ] F.4. Tela da turma tem acoes agrupadas por intencao.
- [ ] F.5. Atividades do aluno usam CTA especifico por estado.
- [ ] F.6. Aluno consegue usar as telas principais confortavelmente em celular.
- [ ] F.7. Professor consegue corrigir varias entregas com menos navegacao.
- [ ] F.8. Tema claro tem contraste adequado.
- [ ] F.9. Foco por teclado e visivel em todos os controles.
- [ ] F.10. Tabelas tem `scope="col"`.
- [ ] F.11. Erros de formulario sao associados aos campos.
- [ ] F.12. Icones decorativos nao poluem leitores de tela.
- [ ] F.13. Links externos indicam nova aba quando aplicavel.
- [ ] F.14. Empty states importantes tem CTA contextual.
- [ ] F.15. `python manage.py check` passa.
- [ ] F.16. Validacao manual professor foi executada.
- [ ] F.17. Validacao manual aluno foi executada.
- [ ] F.18. Resultado final foi reportado com decisoes, arquivos alterados e passos de validacao.
