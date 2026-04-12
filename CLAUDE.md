# Exetasi — Claude Project Context

Free, open-source quiz and exam web application. See `Requirements.md` for the full product specification.

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Quasar 2 (Vue 3 / TypeScript), SPA + Capacitor mobile wrapper |
| Backend | FastAPI (Python) — separate project/repo |
| Database | PostgreSQL |
| State | Pinia (setup-syntax stores) |
| Routing | Vue Router 4 (hash mode) |
| i18n | vue-i18n 11 — all UI strings via translation keys, never hardcoded |
| Package manager | **pnpm** — never use npm or yarn |

## Commands

```bash
pnpm dev        # start dev server (opens browser automatically)
pnpm build      # production SPA build
pnpm lint       # ESLint (flat config)
pnpm format     # Prettier
```

## Project Structure

```
src/
  assets/       static assets
  boot/         Quasar boot files (run before app mount)
  components/   shared components
  css/          global SCSS; quasar.variables.scss for design tokens
  i18n/         translation files (en-US/index.ts, ...)
  layouts/      page wrapper layouts
  pages/        route-level page components
  router/       Vue Router setup
```

## Code Conventions

### Vue
- Always use `<script setup lang="ts">` — no Options API, no `export default defineComponent()`
- Use `defineProps`, `defineEmits`, `defineModel` — no runtime declarations without types
- PascalCase component filenames; Quasar components (`QBtn`, `QCard`, `QInput`) over native HTML equivalents
- Scoped styles in SFCs; global tokens via `quasar.variables.scss`

### TypeScript
- Strict mode is on — no `any`, no unchecked `as` casts
- Prefer `interface` for shapes, `type` for unions/intersections
- Import Quasar config types via `#q-app/wrappers`

### Pinia
- One store per domain concept (e.g., `useAuthStore`, `useExamStore`)
- Use setup-syntax stores (`defineStore('id', () => { ... })`)
- Keep side-effects (API calls) inside actions, not in components

### i18n
- All user-visible strings go through `useI18n().t('key')` — never hardcode UI copy
- Keys are scoped by feature: `exam.title`, `section.description`, etc.

### Styling
- Quasar utility classes preferred over custom CSS where possible
- Custom SCSS lives in `src/css/`; component-scoped styles for component-specific overrides

## Architecture Notes

- This repo is the **frontend SPA only**. The FastAPI backend communicates via REST API.
- Router mode is **hash** (`/#/` URLs) for maximum static-hosting compatibility
- Images are stored externally (S3/GCS/R2/local disk) — never commit binary assets beyond `public/icons`
- i18n is structured for future RTL/multi-language support — use string keys from day one

## Domain Summary

Full specification in `Requirements.md`. Key entity hierarchy:

```
User → Organization → Exam → Version → Section → Question → Answer
```

- Users have a personal org auto-created on registration; username is globally unique
- Only one exam version is **active** at a time; activating one auto-deactivates the previous
- Sections draw a configurable subset of questions from their pool per attempt
- Six question types: multiple choice, open-ended, fill-in-the-blank (`{{n}}` syntax), drag-and-drop ordering, matching, informational
- Scoring varies per type; see Requirements.md → Scoring for formulas
- Manually graded questions (open-ended, manual fill-in-the-blank) flow through the Grading Queue
