# AGENTS.md — cam2web Developer Guide

## Agent Behaviour Rules

**Never** commit, push, or create a GitHub issue without explicitly asking the user first.

The canonical BITPlan Python conventions live at [Agent/Guido/BITPlan](https://media.bitplan.com/index.php/Agent/Guido/BITPlan); this file is project specific and wins on conflict.

---

## Project Overview

`cam2web` is a Python project (requires ≥3.10) providing a **gphoto2 camera web interface** — a single kept-open camera session serving live view, focus and capture over the web. Build system: **hatchling**. Version is sourced from `cam2web/__init__.py`.

Modules live in the `cam` package — the project is `cam2web`, the package is `cam`, the console script is `cam2web`:
- `cam.camera` — the `Camera` backend (single kept-open gphoto2 session)
- `cam.camera_grid` — the pixel `Grid` served to the user
- `cam.os_gphoto2` — operating system level claim / reset handling
- `cam.cam2web_cmd` — the CLI starter

---

## Build / Install Commands

```bash
pip install -e .
scripts/install
```

---

## Test Commands

The test framework is **Python `unittest`** (not pytest). Test classes inherit from `ngwidgets.basetest.Basetest`.

```bash
python -m unittest discover
scripts/test
```

Camera tests skip when no physical device is attached; destructive OS-level tests skip in CI via `Basetest.inPublicCI()`.

---

## Code Style

Formatter: **black** + **isort** via `scripts/blackisort`. Named return variables, type hints and docstrings on public functions, top-level imports, `Optional[X]` over `X | None`.
