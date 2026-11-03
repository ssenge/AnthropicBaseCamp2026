---
name: frontend-design
description: Redesign a Vue 3 application's UI into a modern SaaS-style interface with a vertical navigation sidebar, consistent spacing, and a polished professional look. Use when asked to redesign, modernize, or restyle the app shell or page layouts.
---

# SaaS Frontend Redesign

Change how the app looks, never what it does. Every route, filter, translation, and modal must work the same afterwards.

## Before editing

1. Read `client/src/App.vue` (global styles and shell), `client/src/main.js`, and two representative views.
2. List the hardcoded colors, radii, and spacing in `App.vue`. These become tokens.
3. Check `CLAUDE.md` for the design system and honor it. Here that means slate/gray with status colors, no emojis in the UI, and no new dependencies.

## Shell

- Left vertical sidebar: brand at the top, then one nav item per route, each with an inline SVG icon and a label.
- Slim top bar in the main column for the global filters, language switcher, and profile menu. Dropdowns keep opening downward, so they don't need repositioning.
- Sidebar is fixed to the viewport height. Only the main column scrolls.
- The active route is obvious without relying on color alone.

## Collapsible sidebar

- A toggle switches between full and icons-only. Remember the choice in `localStorage`, wrapped in try/catch.
- Below 900px the sidebar is icons-only regardless of the saved choice, and the toggle is hidden.
- In icons-only mode, each link keeps an `aria-label` and `title`. The toggle has `aria-expanded` and an `aria-label`.

## Visual system

Define tokens as CSS variables on `:root` in `App.vue`, and use them in the global styles:

- Color: surface, canvas, border, text, muted text, accent, and status colors
- Radius: one for cards, one for controls
- Shadow: one subtle card shadow
- Spacing: multiples of 4px

Cards are white with a 1px border, consistent padding, and a clear title row. Tables get a muted header row, comfortable row height, and horizontal scrolling inside their own container, never on the page.

Remove scoped styles that merely duplicate a global style. Keep the ones that do something specific.

## Accessibility and responsiveness

- Visible `:focus-visible` outline on every interactive shell element.
- Text contrast of at least 4.5:1.
- No horizontal page scroll from 375px up. Check 375, 900, and 1440.
- Respect `prefers-reduced-motion` for any added transition.

## Verify

1. `cd client && npm run build` passes.
2. Screenshot every route at 1440 and 375, plus icons-only mode and Japanese at 1440. Look at them; a passing build proves nothing about layout.
3. Check filters, language switching, and modals still work, and the console has no new errors.
4. Report anything you couldn't verify.
