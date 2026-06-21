# Product

## Register

product

## Users

Single-tenant educational portal for **Prof. Toni Coimbra / SEED-PR**. Two primary roles:

- **Professor**: works in batches — manages classes/enrollment, publishes lessons, sends materials, marks activity checks, reads reports. Desktop-first, dense screens, needs clear hierarchy and minimal navigation between repetitive tasks.
- **Aluno (student)**: mobile-first. Opens the portal on a phone to find available lessons, lesson progress, materials and the next study step. Official submissions stay in Google Classroom. Needs scannable cards, visible status, unambiguous CTA.

Admin/superuser is a thin third role (Admin + Status, secondary).

## Product Purpose

Student-delivery layer of a knowledge pipeline: `canonica.md` (PROF-TONI acervo) → import → catalog → publication per class → student. The portal **consumes** the acervo, never rewrites it. Success = professor spends less time navigating and more time teaching; student always knows the next step on a phone.

## Brand Personality

"The Digital Atelier" (DS v2). Three words: **crafted, focused, editorial**. Obsidian dark surfaces with tonal layering, subtle glass, Geist typography, Lucide icons, emerald→cyan CTA gradient. Voice: operational and precise — buttons say exactly what happens ("Sincronizar aulas", "Marcar checks", "Publicar aula", "Salvar"). UI is 100% pt-BR.

## Anti-references

- Generic LMS (Moodle/Classroom blandness). This is an atelier, not a corporate LMS.
- SaaS-cream warm-neutral defaults, hero-metric templates, identical card grids, eyebrow-on-every-section.
- Landing-page redesign of the product — design SERVES the workflow here, not the other way.
- Any new parallel design system. The canonical source is `design_system/design-system.html`.

## Design Principles

1. **Atelier digital, não LMS genérico** — keep obsidian, tonal layering, subtle glass, Geist, Lucide, CTA gradient.
2. **Uma fonte de componentes** — components used 2+ times must live in the design system before broad use.
3. **Professor trabalha em lote** — professor screens prioritize class management, publication, activity checks, reports with clear hierarchy.
4. **Aluno usa celular** — student screens prioritize cards, visible progress, available lessons, unambiguous CTA.
5. **Cor tem função** — green = action/progress, yellow = deadline/attention, red = risk, violet/cyan only as support.
6. **Estados são parte do componente** — every control needs default, hover, active, focus-visible, disabled, loading, empty/error.

## Accessibility & Inclusion

WCAG AA baseline (already worked in Sprint 6 of PRD_UI_UX_AJUSTE.md): body text ≥4.5:1, large ≥3:1 in BOTH dark and light themes; visible keyboard focus on all controls; `scope="col"` on table headers; form errors via `aria-invalid`/`aria-describedby`/`role="alert"`; decorative icons `aria-hidden="true"`; external-new-tab indicated; `prefers-reduced-motion` honored. Mobile-first, no horizontal scroll on student screens at 360px.

## Notes for design work

- **Decision order**: AGENTS.md (invioláveis) > `design_system/design-system.html` > PRD_PROF_DASH.md > Django convention.
- The UI-polish backlog and all decisions already taken live in `PRD_UI_UX_AJUSTE.md` (Sprints 0–8 done). Treat it as the audit baseline — this review is a second pass for regressions and remaining slop.
- Stack is fixed: Django Templates + HTMX + Alpine.js + WhiteNoise. No heavy frontend framework, no chart lib, no IA/Celery. Single quotes, code in English, UI in pt-BR.
