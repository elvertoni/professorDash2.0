# ProfessorDash — Interface Design System

> Direção APROVADA em 2026-06-22. Toda sessão futura lê este arquivo primeiro (DIRETRIZ §5.4).
> Ordem de autoridade: AGENTS.md > DIRETRIZ_DESIGN_PROFESSORDASH.md > este arquivo > PRD > convenção Django.
> Refator é GATED: um estágio por diff, com nota do que mudou e por quê. Sem big-bang.

## Produto
- Portal de aulas single-tenant (Prof. Toni / SEED-PR). Lane **PRODUCT**, não marketing.
- Humano: alunos 14–18 (Curso Técnico Dev Sistemas) lendo aula longa em máquinas Linux travadas;
  + professor (autor). Job: ler com conforto, navegar trilhas, copiar código, acompanhar checklist.
- Feel: claro, técnico, didático, sem hype. Legibilidade > ornamento. Sentence case, verbos ativos.
- Tema por papel: aluno = `light`, professor/admin = `dark` (server-rendered; toggle localStorage).

## Restrições invioláveis
1. **Logo** (`static/logo.svg`): 2 paths — marca C `#00B4D8` + seta `#023E8A`. viewBox
   `0 0 10298.8 10298.8`. NUNCA alterar/recolorir/substituir/revetorizar/achatar. Preservar reserva.
   Única recoloração já autorizada e aplicada (P0 #1): seta off-brand `#3A86FF` → canônico `#023E8A`.
2. **Degradê decorativo BANIDO** (emerald→violet→cyan). Hierarquia = cor chapada + luminosidade de
   superfície + peso tipográfico + espaço. Máx UM gradiente mono-cyan sutil, se algum. Proibido:
   glassmorphism, blur decorativo, accent neon, sombra colorida, hierarquia só-por-cor.

## Direção (1 parágrafo)
Ferramenta de leitura calma e técnica: superfície neutra dominante, **um único accent — o cyan da
marca `#00B4D8` — usado com restrição** só para ação/realce real. Estrutura por borda + escala de
luminosidade de 3 tiers (borders-only), nunca por degradê ou glass. Tipografia carrega a hierarquia
(tamanho + peso + opacidade). Emerald perde status de marca e vira só `success`.

## Token system (APROVADO)

### Cor — accent único `#00B4D8`
```
--accent:      #00B4D8                 /* brand cyan, canônico, uso restrito */
--accent-ink:  #04222B                 /* texto/ícone SOBRE fill accent (AA) */
--accent-tint: rgba(0,180,216,.14)     /* fundo sutil de realce */
--primary-hsl: 190 100% 42.4%          /* resolve exatamente p/ #00B4D8 em hsla() */
```
Por tema (AA): dark `--accent-text:#34CDEC` `--border-focus:#34CDEC` · light `--accent-text:#0E7490` `--border-focus:#0E7490`.
NÃO definir `--accent-violet` nem `--accent-cta` — eram só fonte do degradê banido; uso removido.

### Foreground (3 níveis + on-accent)
```
            dark       light
--fg         #ECE8E7    #0F172A
--fg-muted   #B0ADB5    #475569
--fg-subtle  #84808C    #57647A
--fg-on-accent = --accent-ink (#04222B)
```

### Superfícies — 3 tiers, luminosidade (colapsa os 7 antigos)
```
                    dark       light
--surface-base      #0B0B0D    #EFF1F5   /* canvas — flat, sem radial */
--surface-raised    #141417    #F8F9FC   /* card, panel, topbar */
--surface-overlay   #1C1C21    #FFFFFF   /* dropdown, popover, sticky, lesson-viewer */
```
Mapa 7→3: bg/bg-2→base · surface/strong/soft/elev/low→raised · high/highest→overlay.

### Bordas — dispositivo estrutural primário (borders-only)
```
                dark                    light
--border         rgba(255,255,255,.08)  rgba(15,23,42,.10)
--border-strong  rgba(255,255,255,.14)  rgba(15,23,42,.16)
--border-focus   #34CDEC                #0E7490    /* ring 2px, UI ≥3:1 */
```

### Semântica — AA sobre superfície, dessaturada
```
              dark       light      tint(bg)
--c-success   #34D399    #047857    rgba(16,185,129,.14)   /* emerald rebaixado: só success */
--c-warning   #FBBF24    #B45309    rgba(251,191,36,.14)
--c-danger    #F87171    #B91C1C    rgba(248,113,113,.14)
--c-info      #38BDF8    #0284C7    rgba(56,189,248,.14)
```

### Elevação — UMA estratégia: borda + luminosidade. Sem sombra colorida
```
--shadow-pop  dark:0 8px 24px rgba(0,0,0,.24)   light:0 8px 24px rgba(15,23,42,.10)
```
Só p/ overlays flutuantes (dropdown/popover); resto = borda. Removidos: `--shell-shadow-tint`
(colorida), `backdrop-filter: blur()` (glass), `--grad-*`, body radial, `.stripe-*` degradê.

### Raio — escala (proíbe 8/9/10/11 cru)
```
--radius-xs 4 · --radius-sm 6 · --radius-md 10 · --radius-lg 14 · --radius-xl 20 · --radius-pill 999
```
Concêntrico: `outer = inner + padding`.

### Espaçamento — grade 4px (TRAVA)
```
--space-1 4 · -2 8 · -3 12 · -4 16 · -5 24 · -6 32 · -8 48 · -10 64 · -12 96
```
**Regra de arredondamento:** faltou 20 → 16 ou 24; faltou 40 → 48. NUNCA reintroduzir off-grid
(7/9/11/13/14/18/22/26/28).

### Tipografia — escala travada 12/14/16/20/24/32/48 + peso por papel
```
--text-caption  12 / 1.4  / 500   meta, label pequeno
--text-ui       14 / 1.5  / 400   corpo de UI
--text-read     16 / 1.7  / 400   corpo de aula (leitura longa)
--text-label    16 / 1.4  / 600
--text-h3       20 / 1.3  / 600
--text-h2       24 / 1.2  / 700
--text-h1       32 / 1.15 / 700   (-0.02em)
--text-display  48 / 1.05 / 800   (-0.03em) — só hero da home
--measure       68ch              cap de leitura .lesson-viewer/.prose (alvo 60–75ch)
```
Órfãos (15/17/19/22/34/38/44/46/56) colapsam na escala. Hero 56→48, h1 de página 36→32.

## Padrões de componente (referência p/ refator)
- **btn-primary** — fill `--accent`, texto `--accent-ink`, sem sombra; hover bg `--accent-text` +
  `scale(.97)`; foco ring `--border-focus`. Altura única, padding na grade.
- **card** — `--surface-raised` + `--border` 1px; hover `--surface-overlay` + `--border-strong`,
  `translateY(-2px)`, sem sombra colorida; `--radius-lg`; stripe de degradê removido.
- **lesson-viewer** — `max-width: --measure`; corpo `--text-read` em `--fg` (não muted); h2 com
  borda-esquerda `--accent`; superfície `--surface-overlay` bordeada; sem blur/sombra colorida.

## Ordem de refatoração (gated, um diff por estágio)
- **P0** — (1) ✅ logo seta `#3A86FF`→`#023E8A`.  (2) escrever token system; remover `--grad-*`,
  `--shell-shadow-tint`, body radial→base flat; aliasar `--shell-*`→novos p/ evitar big-bang.
  (3) remover `blur()` header/topbar; colapsar 7 tiers→3.
- **P1** — (4) ✅ `--c-danger/--c-info/--primary-hsl` definidos; `--accent-violet/--accent-cta` +
  hardcodes `#7c3aed/#db2777` removidos. (5) ✅ degradê/`.stripe-*`/texto-gradiente → accent/success;
  **aliases `--shell-*/--grad-*` REMOVIDOS** — 280 refs swap p/ tokens canônicos (css + 7 templates),
  bloco de alias deletado. (6) ✅ escala de tipo travada (zero font-size órfão). (7) ✅ `--measure`
  capado + contraste corpo. (8) ✅ espaçamento → grade 4px: 140 decls off-grid (7/9/10/11/13/14/18/
  20/22/26/28/30/36/40/56) → `var(--space-*)` (density↓/respiro↑); `.message-stack top:82px` →
  `calc(--topbar-h + --space-4)`. Excluídos (passes próprios): `.dot`/`.hero-preview inset`, 8 hits
  emerald cru (focus ring `.auth-form textarea:focus` + `::selection` → accent), radius. **P1 FECHADA.**
- **P2** — (1=9) ✅ raio cru → escala: 8→sm,11/9/10→md,5/3→xs,999→pill; `50%` círculos mantidos.
  (2=10) ✅ multi-hue → semântico/neutro: callouts exemplo→info, importante→warning, curiosidade→neutro;
  `.badge-violet`/`.tag.s`/`.kpi .ico.violet/.cyan` → neutro; off-brand violet/rose/bright-cyan ZERO.
  Bold `.callout .ct b` → `--fg` (peso, não cor; AA). (3=11) ✅ inline `style=` → classes/tokens:
  32→2 inlines (só `width:{{}}%` dinâmico resta); +bloco utilitários, token `--c-warning-ink`
  (dark #1a1206 / light #fff). (4=12) ✅ AA validado (math gamma-correto; reviewer sem-gamma deu
  falsos-FAIL). Único fix real = bold callout light. Pares verificados todos ≥ piso.
  **ETAPA A FECHADA.**
- **ETAPA B (emerald)** — (5) ✅ bug de cor: `::selection` rgba emerald→`--accent-tint` (+ `color:#fff`
  →`--fg`, corrige light); `.auth-form ...:focus` ring emerald→`--border-focus`. (6) ✅ tokenizar
  success: `.badge-success`/`.atelier-meta .tag.p`/`.callout.dica .ic`/`.kpi .ico.green` rgba cru →
  `--c-success`/`--c-success-tint` (texto cyan errado tb corrigido→success). `rgba(16,185,129` = ZERO
  fora da def `--c-success-tint`. AA success-on-tint ≥4.59 (light) ✅. **ETAPA B FECHADA.**
- **ETAPA C (backlog)** — (7) ✅ sombra estática→borda: `.panel`/`.auth-panel`/`.lesson-shell`/
  `.atelier` → `border 1px var(--border)`; sombra fica só em flutuante (`.mobile-nav-panel`/
  `.notification-panel`/`.account-panel`/`.toast`). (10) ✅ morto/naming: `.lesson-viewer` (órfão,
  zero refs) removido c/ surgery (selectors agrupados c/ `.lesson-diagram` preservados); bug
  `.text-success`/`.text-info` (cyan)→`--c-success`/`--c-info`; sem `.stripe`. (13) ✅ `.kpi` +borda
  (consistência borders-only) + hover `--border-strong`. (9) `.dot` óptico → defer p/ verificação no
  browser (não arredondar cego). (11) doc/mockup off-brand (`design-system.html` stripe-violet/cyan,
  #8b5cf6/#06b6d4) → baixa prioridade, não-runtime, SINALIZADO. (8) ✅ home pass: `.shell-preview`
  sombra→borda; `.hero-preview inset`→`space-5`; `.hero min-height`→`calc(100vh - var(--topbar-h))`;
  hero p/actions→tokens; `.text-gradient-brand` removido (span+regra) — accent fora de identidade.
  (12) ✅ logo ponto-único: `templates/partials/_brand.html` (`{% include %}` em base/auth_base/home,
  `size` param); `logo.svg` intocado; data-uri do mockup deixados (item 11/doc). **ETAPA C FECHADA.**
- **REFATOR COMPLETA — P0+P1+P2+B+C.** Pendências sinalizadas: `.dot` óptico (browser),
  `design-system.html` off-brand (doc pass).

## Checklist "pronto" por tela (DIRETRIZ §6 — obrigatório em P1/P2)
- [ ] Estados: vazio / loading / erro com copy útil (o que houve + o que fazer).
- [ ] Overflow: títulos/nomes longos não quebram layout.
- [ ] Responsivo até mobile real (Galaxy S24+).
- [ ] Foco de teclado visível em todo interativo; navegação por teclado funciona.
- [ ] `prefers-reduced-motion` respeitado; nenhuma animação essencial à compreensão.
- [ ] Contraste AA nos pares texto/superfície e UI/superfície.
- [ ] Dark/light consistente.
