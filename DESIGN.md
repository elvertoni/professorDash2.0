# Design

> Canonical source of truth is `design_system/design-system.html` (DS v2 "The Digital Atelier", ~828 lines, ~180 selectors). This file is a summary index for design agents; when in doubt, open the HTML. The `--shell-*` tokens documented below are the **DS canonical** names (visual source of truth). The **runtime** `static/css/app.css` (`:root` / `[data-theme='light']`) carries the same brand values under a **parallel namespace** — `--accent*` / `--fg-*` / `--surface-*` / `--c-*`. Names differ, brand agrees; the bridge is the mapping table in ["Runtime token namespace"](#runtime-token-namespace-appcss--ds).

## Theme

Dark-first (`color-scheme: dark`), with a fully-supported light theme (`[data-theme='light']`). Obsidian surfaces, tonal layering, subtle glass, tinted shadows, radial brand glows on the body background. Both themes are first-class and must be verified on every change.

## Color (OKLCH-equivalent hex tokens)

### Dark (default)
- Backgrounds: `--shell-bg #040405`, `--shell-bg-2 #09090b`
- Surfaces: `--shell-surface rgba(17,17,20,.92)`, `-strong`, `-soft`, `-elev #111114`, `-low`, `-high`, `-highest`
- Borders: `--shell-border rgba(255,255,255,.06)`, `-strong .12`, `--shell-ghost .04`
- Text: `--shell-text #ece8e7` (never pure #fff), `-muted #b0adb5`, `-soft #84808c`
- Brand: `--shell-primary #10b981` (emerald), `-200 #6ee7b7`; `--shell-secondary #8b5cf6` (violet); `--shell-tertiary #06b6d4` (cyan)
- Semantic: `--shell-success #10b981`, `--shell-warning #fbbf24`, `--shell-danger #f87171` (`-hover #dc2626`), `--shell-info #38bdf8`

### Light
- Bg `#f4f5f9`/`#ebedf3`, surfaces near-white, text `--shell-text #0f172a` / muted `#475569` / soft `#64748b`
- Brand darkened for contrast: primary `#047857`, secondary `#7c3aed`; semantic warning `#b45309`, danger `#b91c1c`, info `#0369a1`

### Gradients (tokens only — no literal gradients in templates)
`--grad-primary` (emerald→cyan 135°), `--grad-cta` (emerald→cyan 45°), `--grad-brand` (mint→violet→cyan 120°). Stripe utilities: `.stripe-cta/.stripe-violet/.stripe-warning/.stripe-cyan/.stripe-success`. Text: `.text-brand/.text-success/.text-warning/.text-info/.text-strong`. Gradientes ficam em superfícies e CTAs, nunca em texto.

**Color has function**: green=action/progress, yellow=deadline/attention, red=risk, violet/cyan=support only.

### Runtime token namespace (app.css ↔ DS)

The DS canonical (`design-system.html`) names its tokens `--shell-*`. The runtime `static/css/app.css` does **not** use those names — it exposes a parallel namespace (`--accent` / `--fg-*` / `--surface-*` / `--border*` / `--c-*` / `--grad-cta`) holding the **same brand values**. There was a historical token fork; both namespaces now agree on the mark (emerald → cyan, cyan = support), differing only in token name. The table below is the authoritative bridge — values are verified against `app.css` `:root` (dark) and `[data-theme='light']`.

> **Decisão Leva 2 (2026-07)**: o namespace `--accent*` foi ratificado como o runtime; os valores foram realinhados ao emerald canônico do Atelier. Ciano é suporte, esmeralda é a ação. `.btn-primary` usa `--grad-cta` (`color: var(--accent-ink)` sobre `background: var(--grad-cta)`). Não renomear tokens do app.css para `--shell-*` — usar esta tabela como ponte.

| DS canônico (`--shell-*`) | Runtime (app.css) | Dark (`:root`) | Light (`[data-theme='light']`) |
|---|---|---|---|
| `--shell-primary` (emerald / ação) | `--accent` | `#10b981` | `#047857` |
| `--shell-primary-200` | `--accent-text` | `#6ee7b7` | `#047857` |
| `--shell-tertiary` (cyan / suporte) | `--accent-support` | `#22d3ee` | `#0e7490` |
| `--shell-text` | `--fg` | `#ece8e7` | `#0f172a` |
| `--shell-muted` | `--fg-muted` | `#b0adb5` | `#475569` |
| `--shell-soft` | `--fg-subtle` | `#84808c` | `#57647a` |
| `--shell-surface` / `-elev` | `--surface-base` | `#0b0b0d` | `#eff1f5` |
| `--shell-surface-*` (raised) | `--surface-raised` | `#141417` | `#f8f9fc` |
| `--shell-surface-*` (overlay) | `--surface-overlay` | `#1c1c21` | `#ffffff` |
| `--shell-border` | `--border` | `rgba(255,255,255,.08)` | `rgba(15,23,42,.10)` |
| `--shell-border-strong` | `--border-strong` | `rgba(255,255,255,.14)` | `rgba(15,23,42,.16)` |
| `--grad-cta` (existe em ambos) | `--grad-cta` | `linear-gradient(45deg, #10b981, #06b6d4 130%)` | `linear-gradient(45deg, #047857, #0e7490 130%)` |
| `--shell-success` | `--c-success` | `#34d399` | `#047857` |
| `--shell-warning` | `--c-warning` | `#fbbf24` | `#b45309` |
| `--shell-danger` (`-hover`) | `--c-danger` (`--c-danger-hover`) | `#f87171` (`#dc2626`) | `#b91c1c` (`#b91c1c`) |
| `--shell-info` | `--c-info` | `#38bdf8` | `#0369a1` |

Notes: (1) cyan appears twice — as the standalone support token `--accent-support` (`#22d3ee` dark) and as the terminal stop of `--grad-cta` (`#06b6d4` dark, the DS `--shell-tertiary` value); both are "suporte", never a primary action surface. (2) `--accent-ink` (`#04222B`) is the on-emerald ink used by `.btn-primary`; `--fg-on-accent` resolves to it. (3) Runtime-only tokens with no `--shell-*` twin: `--accent-tint`, `--border-focus`, the `--c-*-tint` fills, and `--c-warning-ink` — treat them as app.css extensions, not new brand directions.

## Typography

- Body: `--font-body` 'Geist' (sans). Mono: `--font-mono` 'Geist Mono'.
- Editorial signatures: `.eyebrow` and `.tag-disc` carry deliberate tracking — do not flatten. One kicker as brand system ≠ eyebrow on every section (banned).
- `text-wrap: balance` on headings, `pretty` on prose; line length 65–75ch.

## Layout & spacing

- Shell: horizontal site chrome (`site-header`/`site-nav`/`mobile-nav`) — **not** a fixed sidebar (decision D.1). `--topbar-h 68px`.
- Spacing scale: `--space-1..12` (4,8,12,16,24,32,48,64,96px). Radii: `--radius-sm/md/lg/xl/pill`.
- Mobile-first; no horizontal scroll on student screens at 360px. Dense professor tables may scroll-x under `.tbl-wrap` (decision D.4).
- Responsive grids: `repeat(auto-fit, minmax(...))`; flex for 1D, grid for 2D.

## Components (canonical, in design-system.html)

Buttons `.btn` (primary/secondary/outline/ghost/danger + disabled), `.icon-btn`; `.card`, `.kpi`, `.panel`; badges `.badge` + `.tag-disc`; forms `.field/.input/.select/.textarea/.check/.switch/.dropzone`; nav `.nav-item`, `.lesson-nav`; tables `.tbl` (+`.tbl-wrap`); states `.empty/.empty-state`, `.toast`, `.modal`, `.tooltip`, `.skel`; `.avatar`, `.progress`, `.eyebrow`, `.stripe-*`, `.text-*` utilities; lesson reader `.atelier/.atelier-rail/.atelier-body/.prose/.callout (conceito|atencao|dica)/.bento/.exercise/.present`.

App-specific documented wrappers: site chrome (`site-header/site-nav/site-footer/mobile-nav`), header dropdowns (`notification-menu`/`notification-panel` and `account-menu`/`account-panel`/`account-link` — same `details/summary` + glass-panel pattern, avatar-triggered), page wrappers (`classroom-page/catalog-page/lesson-page/narrow-page`), auth (`auth-*`), account page (`account-shell/account-sidebar/account-nav/account-content/account-grid`), notifications (`notification-*`). `*-atelier`/`kpi-card` duplicates were unified into core components (decision D.2) — do not reintroduce them.

**Theme by role** (decision D.5): default `data-theme` is server-rendered per role in `base.html` — aluno = `light`, professor/admin/anônimo = `dark`. The `localStorage` toggle still overrides as a personal preference.

**ADHD-focus patterns** (decision D.6, template-scoped `<style>` in the dashboard/reader templates, tokens `shell-*`): `serie-section`/`serie-header` (professor série→disciplina accordion, Alpine), `dash-collapsible` (native `<details>` secondary panel, closed by default — e.g. Prazos), `dash-tabs`/`dash-tab` (Alpine tab switcher on the aluno dashboard — Agora/Aulas/Turmas), `aluno-progress` (big progress panel), `lesson-actionbar` (sticky single-CTA bar on the lesson reader). Goal: one decision per screen, next action always reachable. **Alpine.js (3.14.1) is loaded in `base.html`** (was missing before; `x-data`/`x-show`/`@click` depend on it); `[x-cloak]{display:none!important}` in `app.css` prevents tab flash.

**Modo apresentação**: superfície standalone de projeção, escura e de alto contraste. `deck.js` transforma a aula em slides semânticos por `<h2>`/bloco, preserva builds progressivos e usa rolagem interna somente quando um bloco indivisível não cabe no piso legível. Controles devem funcionar por clique, teclado/controle remoto e foco visível; roteiro (`N`), tela cheia (`F`) e saída (`Esc`) nunca competem com o conteúdo.

## Motion

Intentional only. Ease-out (quart/quint/expo), no bounce/elastic. Every animation needs a `prefers-reduced-motion: reduce` fallback. Don't gate content visibility on class-triggered transitions.

## Absolute bans (impeccable + project)

Side-stripe borders (>1px colored left/right accent), gradient text (`background-clip:text`), glassmorphism-as-default, hero-metric template, identical card grids, tiny uppercase tracked eyebrow on every section, numbered `01/02/03` section markers as scaffolding, text overflowing its container at any breakpoint. New parallel design system. Literal gradients/hex in templates when a token exists.
