# Contributing

Read `CLAUDE.md` and `.claude/plans/mvp-plan.md` first. The plan on `main` is canonical.

- **Branches:** one per stream/topic: `stream-a/loader`, `stream-b/player-page`, ... Claude sessions use one git worktree each.
- **PRs to `main`**, small and frequent, squash-merge, rebase on `main` before merging. Every PR updates the progress tracker in `.claude/plans/mvp-plan.md`.
- **File ownership:** only edit files your stream owns (table in the plan). Need a change elsewhere? Comment on a PR / ask the owner, or open a one-line PR the owner merges within the hour. `main.py`, `package.json`, `requirements.txt`, `Makefile` belong to Stream A.
- **Contract changes** (`backend/app/schemas/`, `contract/`, `frontend/src/api/types.ts`, `SCHEMA.md`, `metrics/SPEC.md`) go through a PR that updates all of them together, regenerates fixtures, and is announced to every stream.
- **Tests:** `make test` must pass (backend `pytest`, frontend `tsc`). The contract test fails if a fixture or route breaks the schema.
- **Design:** every frontend page/component follows the Figma design (rule and frame IDs in `CLAUDE.md`, "Frontend design rule"). Compare a screenshot with the frame before opening the PR.
- **Language:** UI in pt-BR; code, comments, commits and docs in English.
- **Data:** only the supplied JSON; no external sources. Never commit secrets (`.env` is ignored; the LLM key is optional).
- **Dev:** `make setup` once, then `make dev` (backend :8000 + frontend :5173, proxy `/api`). Frontend only, no backend: `make dev-mock`.
