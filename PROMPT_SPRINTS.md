# PROMPT_SPRINTS — executor de sprints do ProfessorDash

> Prompt reutilizável para conduzir o agente sprint a sprint. Troque `{N}` pelo número da sprint
> (0 → 12). Rode **uma sprint por vez**, em ordem, respeitando dependências.

---

Analise com cuidado todos os detalhes de `@AGENTS.md` (regras invioláveis), `@PRD_PROF_DASH.md`
(especificação e fonte de verdade do domínio), `@PROMPT_BUILD_PROF_DASH.md` (processo),
`@design_system/design-system.html` (UI obrigatória) e do código, implementações e padrões já
realizados no projeto. Releia essas fontes a cada sprint.

Em seguida execute a **"Sprint {N}"** descrita na seção **"## 9. Sprints de Desenvolvimento"** do
`PRD_PROF_DASH.md`.

Regras de execução:

- Implemente **todas** as tarefas da Sprint {N} antes de declará-la concluída; não exceda o escopo
  da sprint atual nem antecipe sprints futuras.
- Respeite as dependências de sprints anteriores.
- Marque `[x]` no checklist do PRD conforme finalize cada tarefa. **Ignore** tarefas já marcadas com `[x]`.
- Ambiguidade: decida com a melhor prática Django e **documente a decisão no PRD** (não em comentário solto).
- Ordem de prioridade em conflito: regras invioláveis (`AGENTS.md`) > `design_system/design-system.html` >
  `PRD_PROF_DASH.md` > convenção nativa do Django.
- Git é do humano: **não** faça commit/push a menos que solicitado.
- Sem testes automatizados (decisão do projeto).
- Ao final, reporte: o que foi feito, decisões tomadas e **como validar manualmente** (ex.: `runserver`).
