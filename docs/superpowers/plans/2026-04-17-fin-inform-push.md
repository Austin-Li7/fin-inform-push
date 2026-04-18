# Financial Intelligence Push Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first Python tool that turns U.S. macro and market news into three Obsidian-ready daily briefings.

**Architecture:** Use a small Python package with clear layers for article models, briefing window selection, summary rendering, and note output. Start with demo data so the end-to-end shape is visible immediately, while keeping real feed ingestion as a next-step extension point.

**Tech Stack:** Python 3.13, standard library (`dataclasses`, `datetime`, `pathlib`, `argparse`, `unittest`)

---

### Task 1: Project Skeleton And Demo Contract

**Files:**
- Create: `fin_inform_push/__init__.py`
- Create: `fin_inform_push/models.py`
- Create: `tests/test_pipeline.py`

- [ ] Define article, briefing window, and note models in `fin_inform_push/models.py`
- [ ] Write failing tests in `tests/test_pipeline.py` for briefing selection and markdown rendering
- [ ] Run `python3 -m unittest tests.test_pipeline -v` and confirm failure before implementation

### Task 2: Briefing Pipeline

**Files:**
- Create: `fin_inform_push/pipeline.py`
- Modify: `tests/test_pipeline.py`

- [ ] Implement window filtering and deterministic ordering in `fin_inform_push/pipeline.py`
- [ ] Implement markdown rendering with summary bullets, original links, and scenario analysis
- [ ] Run `python3 -m unittest tests.test_pipeline -v` and confirm green

### Task 3: Demo Experience

**Files:**
- Create: `fin_inform_push/demo_data.py`
- Create: `fin_inform_push/cli.py`
- Create: `README.md`

- [ ] Add demo article fixtures covering premarket, midday, and post-close
- [ ] Add CLI entrypoint that writes generated notes into `demo_output/`
- [ ] Document how to run the preview and how the real-source phase will plug in later

### Task 4: Verification

**Files:**
- Modify: `tests/test_pipeline.py`

- [ ] Run `python3 -m unittest -v`
- [ ] Run `python3 -m fin_inform_push.cli --demo --date 2026-04-17`
- [ ] Review generated markdown files in `demo_output/2026-04-17/`

### Assumptions

- [ ] First pass uses local demo data instead of live feeds so the user can review output shape immediately.
- [ ] Note delivery target is Obsidian-compatible markdown files; direct Obsidian REST push is a follow-up step after format approval.
