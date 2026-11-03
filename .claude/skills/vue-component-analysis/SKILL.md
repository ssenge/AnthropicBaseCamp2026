---
name: vue-component-analysis
description: Analyze the structure of Vue components and suggest performance and code-reuse optimizations. Use when asked to audit, review, or optimize Vue components or views. Read-only; reports findings without editing.
---

# Vue Component Analysis

Report on `client/src/views` and `client/src/components`, or on the files the user names. Do not edit anything unless the user asks.

## 1. Measure

Run the bundled script from the repo root:

```bash
node .claude/skills/vue-component-analysis/scripts/analyze.mjs [paths...]
```

It prints one JSON object per component: line counts per block, API style, and mechanical findings. Treat the output as leads and confirm each one in the source before reporting it. The script reads text with regexes and can be wrong.

## 2. Judge what the script can't

Read the largest components and the ones with findings. Look for:

**Performance**
- Methods called from the template that do derived work and should be `computed`
- `watch` calls that reload everything when a `computed` over existing data would do
- Heavy views imported eagerly in `main.js` that could use route-level `() => import(...)`
- `v-if` on frequently toggled content where `v-show` fits

**Reuse**
- The same helper in several files (`formatDate`, status-to-class maps, the loading/error pattern); name each file and propose one composable or util
- Template blocks repeated across views that could be a component
- Helpers that duplicate `client/src/utils/currency.js` or `useI18n`

## 3. Report

Rank by impact. For each finding give `file:line`, what is wrong, the concrete change, and the effort (S/M/L). Say which findings you confirmed by reading the code. Skip style opinions and anything without a measurable or maintainability payoff. If a component is fine, say so.
