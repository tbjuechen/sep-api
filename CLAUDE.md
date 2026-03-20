# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

UCAS (University of Chinese Academy of Sciences) SEP educational administration system API proxy. Provides both a RESTful API (FastAPI) and a CLI tool (Click) for interacting with the SEP system: login with captcha recognition, course listing, course search, and course selection.

Language: Chinese (code comments, UI strings, data models use Chinese field names like `课程编码`, `课程名称`).

## Commands

```bash
# Setup (full install with API server + Tesseract)
pip install -e ".[all]"

# Minimal install (CLI only)
pip install -e .

# Run API server (requires [api] extra)
sep-api serve
uvicorn sep_api.api:app --reload

# Run tests
pytest
pytest tests/test_client.py            # single file
pytest tests/test_client.py::test_name # single test

# Lint and format
ruff check src/
ruff format src/
```

## Architecture

The package lives in `src/sep_api/` with entry point `sep-api` (defined in pyproject.toml `[project.scripts]`).

- **`client.py`** — Core `SEPClient` class. Async HTTP client (httpx) that manages session state, handles RSA password encryption, login flow (including two-factor auth via `SEPTwoFactorAuthError`), HTML parsing (lxml/xpath), course operations. All network methods are async.
- **`api.py`** — FastAPI app exposing RESTful endpoints. Stores `SEPClient` instances in an in-memory `_sessions` dict keyed by `session_id`. Lifespan handler cleans up sessions on shutdown.
- **`cli.py`** — Dual-mode Click CLI. Without a subcommand → interactive TUI (Rich + InquirerPy). With subcommands (`login`, `courses`, `search`, `select`, `serve`) → agent/script-friendly mode. Pass `--json` for machine-readable output. Session state persisted via `.sep_session.json`.
- **`models.py`** — Pydantic models for API request/response schemas. Course model fields use Chinese names matching the parsed HTML table headers.
- **`captcha.py`** — Pluggable captcha recognition with strategy pattern: `BaseCaptchaHandler` ABC with `TesseractHandler`, `AntiCAPHandler`, `ChaoJiYingHandler` implementations. `CaptchaHandler` facade auto-falls back from AntiCAP to Tesseract on failure.
- **`login.py`** (root) — Standalone interactive login script (not part of the package). Saves session to `.sep_session.json`.

### Two separate domains

Auth goes through `sep.ucas.ac.cn` (HTTPS). Course operations (list, search, select) go through `xkgo.ucas.ac.cn:3000` (HTTP). The client handles cross-domain cookie/session sharing via the same `httpx.AsyncClient`.

### Login & two-factor auth flow

`SEPClient.login()` posts to `/slogin` with `follow_redirects=False`. If the response redirects to a `userVisit` path, two-factor auth is required — raises `SEPTwoFactorAuthError` (subclass of `SEPAuthError`) with `email`/`phone` fields. The caller then uses `send_email_code()`/`send_phone_code()` + `verify_two_factor()` to complete auth.

## Key Patterns

- All HTTP interactions use `httpx.AsyncClient` with browser-like headers and manual redirect handling (`follow_redirects=False` for login to detect two-factor redirects).
- HTML responses are parsed with `lxml.etree.HTML()` + XPath expressions.
- Captcha defaults to AntiCAP (local ONNX model inference, no API key needed) with automatic fallback to Tesseract on failure. Change by passing `method` to `CaptchaHandler` (`tesseract`, `anticap`, `chaojiying`).
- Session files (`.sep_session.json`, `captcha.png`) are gitignored runtime artifacts.

## Requirements

Python >= 3.11. Core deps: httpx, lxml, cryptography, pillow, loguru, pydantic, click, rich, InquirerPy, python-dotenv. Optional: `[api]` adds fastapi + uvicorn; `[tesseract]` adds pytesseract + numpy; `[all]` includes both. Ruff configured with `line-length = 100`.
