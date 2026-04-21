# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Cleanacelerai PRO is a **Windows-only** desktop utility (Python 3.10+ / CustomTkinter) for intelligent file cleanup, duplicate detection, bookmark management and PDF/document classification. Version is tracked in `cleanacelerai/__init__.py` (`__version__`).

## Commands

All commands run from the **repo root** unless noted.

```bash
# Install deps (root requirements = runtime; package requirements = runtime+test)
pip install -r requirements.txt
pip install -r cleanacelerai/requirements.txt

# Run the app (module form — needed so relative imports resolve)
python -m cleanacelerai.run

# Tests — must cd into the package because pytest.ini sets pythonpath=.
cd cleanacelerai && python -m pytest tests/ -v

# Single test / single case
cd cleanacelerai && python -m pytest tests/test_risk_evaluator.py -v
cd cleanacelerai && python -m pytest tests/test_risk_evaluator.py::TestEvaluateFileRisk::test_vscode_is_dotfile -v

# Build Windows executable
pyinstaller cleanacelerai.spec   # output: dist/cleanacelerai.exe
```

Coverage gate is `--cov-fail-under=15` (pytest.ini). The low bar is intentional — the entire `src/ui/` layer has 0% coverage because no headless Tk harness exists. **Raise the threshold when adding service/domain tests, not when adding presenter tests.**

## Architecture

Hexagonal (Clean) + MVP. Dependency direction is strictly inward: `ui → services → domain`, and `ui → infrastructure` for I/O. **Domain must not import from services, infrastructure, or ui.**

```
cleanacelerai/src/
  domain/          pure logic: enums, dataclasses, risk_evaluator, constants
  services/        stateless business logic (scanning, hashing, categorizing)
  infrastructure/  OS side-effects (safe_delete, ConfigService, model cache)
  ui/
    views/         passive CustomTkinter widgets — zero business logic
    presenters/    orchestrate services ↔ views, own the threading
    main_window.py thin orchestrator: builds views, wires presenters, nav
```

### Non-obvious invariants

- **Threading model.** Every long operation (scan, SHA-256 hash, web fetch, PDF parse) runs on a daemon thread inside a presenter. UI updates must go back to the Tk main thread via `view.after(0, callback)` — never touch widgets from the worker thread directly.
- **Services are stateless.** They take inputs + an optional progress callback and return data. Do not add instance state to a service; put coordination state in the presenter.
- **Risk engine is the safety net.** `domain/risk_evaluator.py::evaluate_file_risk` is the single source of truth for "can this be deleted?". It layers Windows system paths → critical extensions → dotfiles → user keywords → user folders → personal profile folders. Any new deletion feature must route through it, not re-implement the check.
- **Bookmark organize rebuilds, never patches.** Chrome Sync makes in-place bookmark-by-id edits fragile, so `services/bookmark_manager.py` extracts all URLs, categorizes them, then rebuilds the bookmark bar from scratch. Preserve that pattern when extending.
- **Windows-specific paths.** `infrastructure/file_system.py::safe_delete` handles the `\\?\` long-path and `\nul` workarounds via `cmd /c del`. On non-Windows platforms this path silently no-ops — treat cross-platform work as an explicit refactor, not a drop-in.
- **Config persistence.** `ConfigService` reads/writes `~/.cleanacelerai/config.json` with defaults-merge on load (so new keys added in later versions appear automatically). Deep-categorization cache lives next to it in `deep_cache.json`.
- **Navigation side effect.** `MainWindow._select_frame("duplicados")` re-pushes the latest protected keywords/folders into `DuplicatesPresenter` before showing the frame. When adding new presenters that depend on live Rules state, follow the same pattern instead of snapshotting at construction time.

### Adding a new feature tab

1. Add a dataclass/enum to `domain/models.py` if needed.
2. Put pure logic in `services/<name>.py` (no Tk imports).
3. Create `ui/views/<name>_view.py` — inherit `ctk.CTkFrame`, expose setter/getter methods, no business logic.
4. Create `ui/presenters/<name>_presenter.py` — takes the view, runs services on a daemon thread, updates view via `after(0, ...)`.
5. Register view + presenter in `ui/main_window.py` (`_build_content_area`, `_wire_presenters`, `_TITULOS`, and the sidebar `nav_items` list).

## Roadmap flags in README

The README "Roadmap" list (`Face recognition`, `TF-IDF + scikit-learn`, `Drag-and-drop`, `Export reports`) reflects planned work. Check it before proposing the same feature as new.
