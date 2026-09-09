# Design — Volta Atelier

> Fonte canônica de verdade: `design_system/design-system.html` (DS v3 "Volta Atelier"). Este documento é o índice de referência para o design e para os agentes. O runtime `static/css/app.css` integra os tokens do Volta Atelier (`--ink`, `--bone`, `--signal`, `--panel`, `--line`) mapeados de forma retrocompatível para o shell educacional.

## Identidade & Estética

Brutalismo editorial refinado, alto contraste, texturas e superfícies calculadas, tipografia de estúdio (**Archivo** para títulos e displays, **JetBrains Mono** para metadados, corpo e labels). Botões em formato pílula com wipe hover em `--signal`, chips circulares flutuantes e foco radical em legibilidade e hierarquia.

A marca oficial é a ligadura **TC** de `static/logo.svg`, sincronizada com `portifolio_tc/assets/logo.svg`. O favicon usa o corte óptico próprio de `static/favicon.svg`; não derive o favicon reduzindo a marca horizontal.

## Temas (Dark & Light)

- **Professor / Admin:** Dark mode por padrão (`:root`), simulando superfície de trabalho noturna de ateliê.
- **Aluno:** Light mode por padrão (`[data-theme='light']`), priorizando conforto visual em telas móveis e sala de aula (fundo off-white editorial de alta legibilidade, não branco puro ofuscante).
- O toggle do usuário (`localStorage`) continua permitindo alternância manual.

## Paleta de Cores e Tokens

### Tokens Oficiais Volta Atelier

| Token Volta | Dark (`:root`) | Light (`[data-theme='light']`) | Função / Aplicação |
|---|---|---|---|
| `--ink` | `#141414` | `#f6f5f2` | Fundo principal da página |
| `--ink-deep` | `#0d0d0d` | `#eceae5` | Poços, rodapé e fundos recuados |
| `--panel` | `#1c1c1e` | `#ffffff` | Superfície primária de cards e modais |
| `--panel-2` | `#232326` | `#faf9f7` | Cards elevados, tabelas e dropdowns |
| `--line` | `rgba(255, 255, 255, .11)` | `rgba(20, 20, 20, .10)` | Divisores e bordas sutis |
| `--line-2` | `rgba(255, 255, 255, .20)` | `rgba(20, 20, 20, .18)` | Bordas ativas e contornos interativos |
| `--bone` | `#f4f3f0` | `#141414` | Texto primário (alto contraste) |
| `--muted` | `#8e8e95` | `#5c5c63` | Texto secundário e legendas |
| `--dim` | `#5c5c63` | `#8e8e95` | Texto terciário e metadados discretos |
| `--signal` | `#fb3732` | `#fb3732` | Acento vibrante, hover de botões e alertas |
| `--amber` | `#ffa31a` | `#d97706` | Prazos próximos e atenção |
| `--volt` | `#3b49e4` | `#2563eb` | Apoio, links complementares e 3D |
| `--emerald` | `#10b981` | `#059669` | Conclusão, checks de aula e progresso |

### Mapeamento de Runtime (`app.css` ↔ Volta Atelier)

Para garantir compatibilidade com todo o ecossistema Django, HTMX e Alpine.js existente:

| Variável Runtime (`app.css`) | Mapeamento Volta | Descrição |
|---|---|---|
| `--surface-base` | `var(--ink)` | Fundo da aplicação |
| `--surface-raised` | `var(--panel)` | Superfície de cards |
| `--surface-overlay` | `var(--panel-2)` | Modais, menus e dropdowns |
| `--fg` | `var(--bone)` | Cor principal de tipografia |
| `--fg-muted` | `var(--muted)` | Textos secundários |
| `--fg-subtle` | `var(--dim)` | Textos terciários |
| `--border` | `var(--line)` | Borda padrão |
| `--border-strong` | `var(--line-2)` | Borda enfatizada |
| `--accent` | `var(--signal)` | Cor de ação primária |
| `--accent-text` | `#ffffff` | Texto sobre superfícies de destaque |

## Tipografia

- **Display / Títulos:** `'Archivo', sans-serif` (pesos 600, 700, 800, 900).
- **Corpo / Metadados / Mono:** `'JetBrains Mono', monospace` (pesos 400, 500, 600).
- As fontes do sistema ficam versionadas em `static/fonts/archivo-latin.woff2` e `static/fonts/jetbrains-mono-latin.woff2`; Geist permanece disponível para a apresentação de aulas.

## Componentes Chave

- **Botão `.btn`:** Arredondamento pílula (`border-radius: 999px`), preenchimento `--bone` e texto `--ink`, com micro-interação de subida de camada `::before` em `--signal` no hover.
- **Navegação `.navchain`:** Pílula encadeada flutuante com blur de fundo e indicador `.on` com borda `--signal`.
- **Chips `.chip`:** Pílulas compactas mono para tags, séries e disciplinas.
- **Formulários:** Inputs e selects com fundo `--panel`, borda `--line-2`, texto `--bone`, foco com outline/borda `--signal`.
- **Tabelas densas:** `.tbl` com cabeçalhos mono em caixa-alta e separadores `--line`.

## Direção de Movimento — Atelier Cinético

O movimento é uma camada funcional do Volta Atelier: orienta entrada, continuidade espacial e confirmação de estado. Não é decoração independente.

- **Momento autoral:** a página entra como uma composição editorial única por `opacity + blur + clip-path + translate`, com stagger curto entre blocos. O conteúdo permanece visível sem JavaScript e há fallback de 2,2 s.
- **Navegação:** header sticky ganha profundidade somente após scroll; o indicador ativo desenha a régua `--signal`; View Transitions conectam páginas e troca de tema quando suportadas.
- **Superfícies:** cards, KPIs e painéis recebem luz tonal localizada pelo ponteiro em desktop. Em touch, o layout permanece estático e completo.
- **Estado:** barras de progresso crescem da origem; menus, details, dialog e toast usam entrada física própria. Botões mantêm o wipe canônico.
- **Performance:** eventos de scroll e ponteiro compartilham atualizações via `requestAnimationFrame`; observers se desconectam após a entrada.
- **Acessibilidade:** `prefers-reduced-motion: reduce` desativa loops, reveals, deslocamentos e transições de navegação. Foco visível e semântica não dependem de animação.

### Primitivas Canônicas

- `.scroll-progress` — régua fixa de leitura.
- `[data-motion][data-motion-state]` — reveal progressivo com fallback visível.
- `.kinetic-surface` / `.has-pointer` — luz tonal responsiva a ponteiro fino.
- `.kinetic-hero` e `.journey-track` — assinatura da página pública e fluxo acervo → turma → aluno.
- `.lesson-actionbar` — ação persistente do leitor, agora centralizada no runtime.
