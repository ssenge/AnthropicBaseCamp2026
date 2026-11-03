# Audit action plan (2026-11-03)

Security, performance and UX reviewers audited the code in parallel and challenged each other's severity ratings. They read code only; nothing was run or measured. This is a local demo with mock data, so nothing rates above Medium for security or performance today. "Prod" is the rating for a real deployment.

Agent teams weren't available in the session, so this ran as three subagents messaging each other, not as a true team. Spot checks confirmed items 1, 2, 3, 5 (corrected) and 14. The rest come from the reviewers' reports.

## P1: fix first

| # | Issue | Evidence | Demo | Prod |
|---|---|---|---|---|
| 1 | Modals have no dialog role, Esc-to-close or focus trap, and icon-only close buttons have no accessible name | `client/src/components/ProductDetailModal.vue:4-8`, `TasksModal.vue` | High (UX) | High |
| 2 | No auth on any route, including writes; the client hardcodes the user as logged in | `client/src/composables/useAuth.js:92`, `server/main.py` | Low | Critical |
| 3 | CORS allows any origin with credentials | `server/main.py:54-55` | Low | High |

Fix 2 and 3 together before any real deployment.

## P2: fix soon

| # | Issue | Evidence | Demo | Prod |
|---|---|---|---|---|
| 4 | Task add, delete and toggle failures only reach the console, with no UI error or rollback. Reviewers disagreed on the rating. | `client/src/App.vue:108-110`, `:129`, `:150` | Medium | Medium |
| 5 | A slower earlier response can overwrite a newer one after a filter change. Reports and Restocking are guarded; Orders and Dashboard are not. | `client/src/views/Orders.vue:163`, `Dashboard.vue:676` | Low | Medium |
| 6 | List endpoints are unbounded, with no pagination | `server/main.py` | Low | Medium to High |
| 7 | Fixed since this audit: purchase orders now have routes and a modal | | | |
| 8 | Filter labels have no `for`/`id`, clickable rows are mouse-only, and focus outlines are removed | `client/src/components/FilterBar.vue:6-7`, `Inventory.vue:55-56`, `Dashboard.vue:191` | Medium | Medium |
| 9 | Fixed since this audit: the redesign removes page-level overflow down to 375px | | | |

## P3: backlog

| # | Issue | Evidence | Rating |
|---|---|---|---|
| 10 | Profile menu has no `aria-expanded`; task delete is a bare `×` with no confirmation | `client/src/components/ProfileMenu.vue:3-6`, `TasksModal.vue:86-90` | Medium (UX) |
| 11 | Top-products computed is O(orders × items × inventory); four requests per filter change | `client/src/views/Dashboard.vue:501`, `:567-570` | Low, Medium in prod |
| 12 | Restock orders can be replayed because stock is never deducted | `server/main.py`, `create_restock_order` | Low, Medium in prod |
| 13 | Tasks and restock orders grow without bound; no title length cap | `server/main.py` | Low, Medium in prod |
| 14 | Server binds to `0.0.0.0` instead of `127.0.0.1` | `server/main.py:514` | Low, High in prod |
| 15 | Free-form filter strings; `month` is a substring match. No injection risk without a database. | `server/main.py:31`, `:35-49` | Low |
| 16 | Hardcoded English in modals; `<html lang>` never changes | `client/src/components/ProductDetailModal.vue:7`, `client/index.html:2` | Low |
| 17 | `TasksModal` purple gradient breaks the slate palette | `client/src/components/TasksModal.vue:391` | Low |
| 18 | Eager view imports, template-called filters, O(n²) backlog check | `client/src/main.js:4-11`, `Demand.vue:17-64`, `server/main.py:322` | Low |
| 19 | Unpinned dependencies; lockfiles are gitignored on purpose per `CLAUDE.md` | `server/requirements.txt` | Low |
| 20 | Loading state flickers on every filter change | `client/src/views/Dashboard.vue:563`, `Orders.vue:158` | Low to Medium |

## Checked and clean

No `v-html`, `innerHTML` or `eval` in `client/src`. Tasks API input validation is good. Restock pricing is computed on the server. No secrets in tracked files.
