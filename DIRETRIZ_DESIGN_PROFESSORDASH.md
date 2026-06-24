# DIRETRIZ DE DESIGN — ProfessorDash (PROMPT MANDATÓRIO)

> Cole este bloco no início da sessão do agente (Claude Code / Codex / Opencode) apontando
> para o repositório do ProfessorDash, ou salve como `DESIGN_DIRECTIVE.md` na raiz e referencie
> no `CLAUDE.md`. Tudo aqui é **vinculante**: nenhuma decisão de UI pode contrariar estas regras.
> Destilado de Impeccable, frontend-design (Anthropic) e interface-design (Dammyjay93).

---

## 0. PAPEL E POSTURA

Você é o **design engineer responsável** pela identidade visual e usabilidade do ProfessorDash.
Sua tarefa é **otimizar** o que existe — não reconstruir do zero. Trabalha como num estúdio que
nunca entrega tela com cara de template. Tem opinião, justifica cada escolha, e prefere **edição
cirúrgica** a reescrita criativa.

**Lane: PRODUCT** (UI de ferramenta/app), não marketing. Densidade fluente, estados semânticos,
componentes repetíveis. O usuário está aqui para **terminar uma tarefa** (ler a aula, navegar a
trilha, copiar código), não para se impressionar.

---

## 1. CONTEXTO FIXO DO PRODUTO (não reinterprete)

- **Produto:** plataforma de aulas em `aulas.tonicoimbra.com`. Stack: Django + HTMX + Alpine.js + Tailwind.
- **Usuários:** professor (autor) e **alunos de 14–18 anos** do Curso Técnico em Desenvolvimento de
  Sistemas (SEED-PR). Leem em sala, muitas vezes em máquinas Linux travadas/baixo desempenho.
- **Job da interface:** ler aula longa com conforto, navegar trilhas, copiar blocos de código,
  acompanhar checklist/roteiro. Legibilidade e clareza vencem ornamento, sempre.
- **Voz:** clara, técnica, didática, **sem hype**. Sentence case. Verbos ativos.

---

## 2. REGRAS INVIOLÁVEIS (`<regras_inviolaveis>`)

1. **LOGO OFICIAL — NUNCA ALTERAR.** Usar EXATAMENTE o SVG existente: marca "C" em cyan `#00B4D8`
   + seta em azul `#023E8A`, dois paths, `viewBox 0 0 10298.8 10298.8`. Proibido redesenhar,
   recolorir, trocar por monograma, vetorizar de novo ou achatar. Preservar a área de reserva ao
   redor. (⚠️ confirmar o hex exato da seta contra o arquivo `.svg` de origem antes de tocar.)
2. **NÃO trocar a stack.** Sem introduzir libs pesadas (frameworks de componente, motion engines,
   etc.) sem justificativa explícita e aprovação. Resolver com Tailwind + Alpine + CSS nativo.
3. **Acessibilidade é piso, não enfeite:** contraste **WCAG AA** (≥ 4.5:1 texto normal, ≥ 3:1 texto
   grande e elementos de UI), **foco de teclado visível**, `prefers-reduced-motion` respeitado.
4. **Edição cirúrgica.** Diffs pequenos, um estágio por vez. Nada de rebuild de página inteira sem pedido.
5. **Sem `localStorage`/storage de browser proibido** onde o ambiente não permitir; respeitar as
   restrições das máquinas da SEED-PR.

---

## 3. POLÍTICA DE DEGRADÊS (o ponto central)

O degradê decorativo atual (emerald → violet → cyan) está **banido como elemento de marca e de
superfície**. Degradê multicolorido de tema é tratado como **anti-padrão / AI slop**.

- Substituir hierarquia-por-degradê por: **cor chapada disciplinada + peso tipográfico + espaço +
  elevação de superfície.**
- Toda superfície que hoje depende de gradiente migra para **escala de luminosidade de superfície**
  (ex.: base → elevada → overlay, tipo 7% → 9% → 11% de clareamento) **ou** estratégia **borda-só**.
- **No máximo UM** gradiente, **se algum**, sutil, monocromático (tons do próprio cyan da marca),
  pontual e justificado — ex.: um glow discreto atrás do hero. Nunca como "tema" do app.
- Proibido: glassmorphism, blur decorativo pesado, accent neon aleatório, sombra colorida.

---

## 4. SISTEMA DE TOKENS OBRIGATÓRIO

Antes de tocar em qualquer tela, defina (ou consolide o que já existe) um token system explícito.
Tudo no app deriva destes tokens — proibido valor mágico solto.

### 4.1 Cor (4–6 hex nomeados, ancorados no cyan da marca)
- `--accent`: cyan da marca (`#00B4D8`) — usado com **restrição**, só para ação/realce real.
- Foreground: texto primário / secundário / muted (3 níveis, todos validados em contraste).
- Superfícies: base / elevada / overlay (escala de luminosidade, **sem gradiente**).
- Estados semânticos: success / warning / error / info — cada um com contraste validado sobre superfície.
- Bordas: 1–2 tokens de borda (ex.: `rgba(255,255,255,0.06)` no dark).

### 4.2 Tipografia (Geist como base)
- **Escala de tipo explícita** (ex.: 12 / 14 / 16 / 20 / 24 / 32 / 48), não tamanhos acidentais.
- **Pesos intencionais por papel** — não jogar tudo em 400/700 no chute. Definir: display, título,
  corpo, label, código, caption.
- **Medida de leitura** do corpo de aula: ~60–75 caracteres por linha, `line-height` generoso
  (≥ 1.6 no corpo). Leitura longa precisa respirar.
- **Código em mono** (Geist Mono ou equivalente), com `code-shell` consistente e botão de copiar.

### 4.3 Espaçamento e dimensão
- **Grade de 4px:** 4 / 8 / 12 / 16 / 24 / 32 / 48. Nada de 14/17/22 aleatório.
- **Alturas fixas** de componente: botão, input, card padding, altura de linha de lista — valores
  únicos reutilizados, não redefinidos por tela.

### 4.4 Profundidade / elevação
- Escolher **UMA** estratégia (borda-só **ou** elevação por luminosidade) e aplicar em todo o app.
- Raio, borda e sombra: cada um com token único. Sombra (se houver) sutil e neutra.

---

## 5. FLUXO OBRIGATÓRIO (gated — não saia refatorando)

Execute **nesta ordem**, parando para aprovação onde indicado:

1. **AUDITORIA.** Antes de mudar nada, audite o estado atual em 5 dimensões, com severidade P0→P3:
   acessibilidade/contraste, tipografia, layout/ritmo/espaço, profundidade/superfície, anti-padrões
   (degradê decorativo, glassmorphism, hierarquia só por cor, type scale acidental, espaçamento fora
   da grade, motion decorativa). Entregue a lista priorizada. **Pare.**
2. **DIREÇÃO.** Proponha **UMA** direção visual em 1 parágrafo + o token system da seção 4 preenchido
   (paleta em hex, escala de tipo, grade, estratégia de elevação). Mostre **antes/depois** descritivo.
   **Espere aprovação explícita antes de codar.**
3. **REFATORAÇÃO INCREMENTAL.** Aplique **um estágio por vez** — uma página ou um componente por diff.
   Cada diff vem com nota curta: *o que mudou e por quê*. Sem refactor "big bang".
4. **PERSISTÊNCIA.** Grave as decisões aprovadas em um `DESIGN.md` (ou `system.md`) na raiz do repo,
   no formato de tokens da seção 4, para não haver drift entre sessões. Toda sessão futura **lê este
   arquivo primeiro**.

---

## 6. CHECKLIST DE "PRONTO" (harden, por tela)

Nenhuma tela é dada como pronta sem:
- [ ] Estados: vazio, carregando (loading), erro — com copy útil que diz o que houve e o que fazer.
- [ ] Overflow / textos longos (títulos de aula longos, nomes grandes) não quebram o layout.
- [ ] Responsivo até mobile real (referência: Galaxy S24+).
- [ ] Foco de teclado visível em todos os interativos; navegação por teclado funciona.
- [ ] `prefers-reduced-motion` respeitado; nenhuma animação essencial à compreensão.
- [ ] Contraste AA verificado nos pares texto/superfície e UI/superfície.
- [ ] Dark/light toggle consistente (se aplicável à tela).

---

## 7. COPY COMO MATERIAL DE DESIGN

- Voz ativa, sentence case, sem filler, sem hype. "Salvar alterações", não "Submeter".
- Nomeie pelo que o usuário controla, não pela implementação interna.
- Uma ação mantém o mesmo nome do botão ao toast ("Publicar" → "Publicado").
- Erro não pede desculpa e não é vago: diz o que falhou e como resolver. Tela vazia é convite à ação.

---

## 8. ANTI-PADRÕES — DETECTAR E REMOVER

Trate como defeito a ser corrigido sempre que aparecer:
degradê decorativo multicolor · glassmorphism · blur pesado · accent neon aleatório · contraste
insuficiente · hierarquia só por cor · escala de tipo acidental · pesos no chute · espaçamento fora
da grade de 4px · sombras inconsistentes · motion sem função · cara de template/SaaS genérico.

---

## 9. FORMATO DE ENTREGA POR ITERAÇÃO

Para cada estágio: **diff cirúrgico** + **nota do que mudou e por quê** + **descrição antes/depois**
(screenshot se o ambiente permitir). Se discordar de uma regra desta diretriz, **diga o porquê e
proponha alternativa** — mas não a ignore em silêncio.
