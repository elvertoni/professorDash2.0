# Design

> Canonical source of truth is `design_system/design-system.html` (DS v2 "The Digital Atelier", ~828 lines, ~180 selectors). This file is a summary index for design agents; when in doubt, open the HTML. Tokens below mirror `static/css/app.css` `:root` / `[data-theme='light']`.

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
- Brand darkened for contrast: primary `#047857`, secondary `#7c3aed`; semantic warning `#b45309`, danger `#b91c1c`, info `#0284c7`

### Gradients (tokens only — no literal gradients in templates)
`--grad-primary` (emerald→cyan 135°), `--grad-cta` (emerald→cyan 45°), `--grad-brand` (mint→violet→cyan 120°). Stripe utilities: `.stripe-cta/.stripe-violet/.stripe-warning/.stripe-cyan/.stripe-success`. Text: `.text-gradient-brand/.text-success/.text-warning/.text-info/.text-strong`.

**Color has function**: green=action/progress, yellow=deadline/attention, red=risk, violet/cyan=support only.

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

App-specific documented wrappers: site chrome (`site-header/site-nav/site-footer/mobile-nav`), page wrappers (`classroom-page/catalog-page/lesson-page/narrow-page`), auth (`auth-*`), account (`account-*`), notifications (`notification-*`). `*-atelier`/`kpi-card` duplicates were unified into core components (decision D.2) — do not reintroduce them.

## Motion

Intentional only. Ease-out (quart/quint/expo), no bounce/elastic. Every animation needs a `prefers-reduced-motion: reduce` fallback. Don't gate content visibility on class-triggered transitions.

## Absolute bans (impeccable + project)

Side-stripe borders (>1px colored left/right accent), gradient text (`background-clip:text`), glassmorphism-as-default, hero-metric template, identical card grids, tiny uppercase tracked eyebrow on every section, numbered `01/02/03` section markers as scaffolding, text overflowing its container at any breakpoint. New parallel design system. Literal gradients/hex in templates when a token exists.
