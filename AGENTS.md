# Exetasi — Agent Instructions

Free, open-source quiz and exam web application. Full product specification is in `Requirements.md`.

## Stack

- **Frontend**: Quasar 2 (Vue 3 / TypeScript) SPA; Capacitor for mobile
- **Backend**: FastAPI (Python) — separate project
- **Database**: PostgreSQL
- **State**: Pinia; **Routing**: Vue Router 4 (hash mode); **i18n**: vue-i18n 11
- **Package manager**: pnpm (never npm or yarn)

## Build & Run

```bash
pnpm install    # install dependencies
pnpm dev        # dev server with hot reload
pnpm build      # production build → dist/spa/
pnpm lint       # ESLint check
pnpm format     # Prettier format
```

## Code Rules

1. **Vue SFCs**: always `<script setup lang="ts">` — no Options API
2. **TypeScript**: strict mode; no `any`; no unchecked `as` casts
3. **Components**: PascalCase filenames; use Quasar components over native HTML
4. **Pinia stores**: setup-syntax `defineStore`; one store per domain concept
5. **i18n**: all user-visible strings via `t('key')` — no hardcoded UI copy
6. **Styles**: Quasar utilities first; SCSS in `src/css/`; scoped styles in SFCs
7. **Imports**: `#q-app/wrappers` for Quasar config types; auto-imports are active

## Domain Model

Entity hierarchy: `User → Organization → Exam → Version → Section → Question → Answer`

- Each user has a personal org auto-created on registration
- Exactly one version per exam is active at a time
- Sections draw a randomised subset from their question pool per attempt
- Question types: multiple choice, open-ended, fill-in-the-blank (`{{n}}`), drag-and-drop ordering, matching, informational
- Manually graded answers surface in the Grading Queue

See `Requirements.md` for complete specification including scoring formulas, roles, analytics, and deployment targets.
