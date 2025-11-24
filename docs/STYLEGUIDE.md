# Access AI — Style Guide

This style guide documents the visual system for Access AI: color palette, typography, spacing, components, and accessibility guidance.

## Color Palette
- Primary (Innovation Blue): `#2563eb` — used for main CTAs and highlights.
- Accent (Aqua): `#06b6d4` — used for supportive accents and small badges.
- Background (Deep Indigo): `#0f1724` — app background to convey modern/professional tone.
- Contrast (White): `#ffffff` — primary text on dark background.
- Muted: `#94a3b8` — secondary text.

All primary/contrast pairs meet WCAG AA for large and normal text; run contrast checks for any added tints.

## Typography
- Headings: `Inter` (Google Fonts) — modern, readable, geometric.
- Body: `Lato` (already used) — humanist, comfortable for paragraph text.
- Monospace: `Roboto Mono` — for code samples.

Scale suggestions:
- H1: 48–52px (responsive)
- H2: 28–36px
- Body: 16px (base)
- Small: 14px

## Spacing System
- Use spacing variables: `--space-xs` `--space-sm` `--space-md` `--space-lg` `--space-xl`.
- Follow consistent vertical rhythm; use multiples of 4 or 8px.

## Grid
- 12-column grid; breakpoints at 900px and 560px.
- Use `.grid` utility and `.col-*` classes.

## Buttons
- `.btn-primary` — filled with gradient, strong shadow, clear hover lift.
- `.btn-outline` — neutral alternative for secondary actions.
- Touch target: minimum 44x44px.

## Cards
- Use subtle surface (`--color-card`) with border and soft shadow.
- On hover: slight translateY and stronger shadow for affordance.

## Accessibility Recommendations
- Provide `alt` for all images; if decorative, set `alt=""` and `aria-hidden="true"`.
- Ensure keyboard navigation order is logical and visible focus styles are always present (`:focus-visible`).
- Prefer semantic HTML (landmark roles: `header`, `main`, `nav`, `footer`, `section`, `article`).
- Avoid motion for users with `prefers-reduced-motion`.
- Use ARIA only when necessary and ensure ARIA roles are accurate.

## Motion
- Use subtle transitions (200–300ms) and no autoplaying or attention-stealing animations.
- Stagger entrance animations for lists/cards with mild delays.

## Assets & Icons
- Prefer SVG icons with consistent stroke/size.
- Use modern illustrations for hero (light-weight SVG or optimized PNG) that convey AI + accessibility.

---
Design decisions: the palette combines a trustworthy deep indigo with a bright blue and an aqua accent to signal technology and approachability. Inter + Lato provide a professional but warm typographic pairing, and the spacing/grid system ensures clarity and balance.
