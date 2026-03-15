# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

UCAS (University of Chinese Academy of Sciences) SEP educational administration system API proxy. Provides both a RESTful API (FastAPI) and a CLI tool (Click) for interacting with the SEP system: login with captcha recognition, course listing, course search, and course selection.

Language: Chinese (code comments, UI strings, data models use Chinese field names like `课程编码`, `课程名称`).

## Commands

```bash
# Setup
conda env create -f environment.yml
conda activate sep-api
pip install -e .

# Run API server
sep-api serve
uvicorn sep_api.api:app --reload

# Run tests
pytest

# Lint and format
ruff check src/
ruff format src/
```

## Architecture

The package lives in `src/sep_api/` with entry point `sep-api` (defined in pyproject.toml `[project.scripts]`).

- **`client.py`** — Core `SEPClient` class. Async HTTP client (httpx) that manages session state, handles RSA password encryption, login flow (including two-factor auth via `SEPTwoFactorAuthError`), HTML parsing (lxml/xpath), course operations. All network methods are async.
- **`api.py`** — FastAPI app exposing RESTful endpoints. Stores `SEPClient` instances in an in-memory `_sessions` dict keyed by `session_id`. Lifespan handler cleans up sessions on shutdown.
- **`cli.py`** — Click CLI wrapping `SEPClient` async methods via `asyncio.run()`. Global `_logged_in_client` holds session state between subcommands.
- **`models.py`** — Pydantic models for API request/response schemas. Course model fields use Chinese names matching the parsed HTML table headers.
- **`captcha.py`** — Pluggable captcha recognition with strategy pattern: `BaseCaptchaHandler` ABC with `TesseractHandler`, `AntiCAPHandler`, `ChaoJiYingHandler` implementations. `CaptchaHandler` facade auto-falls back from AntiCAP to Tesseract on failure.
- **`login.py`** (root) — Standalone interactive login script that saves session to `.sep_session.json`.

## Key Patterns

- All HTTP interactions use `httpx.AsyncClient` with browser-like headers and manual redirect handling (`follow_redirects=False` for login to detect two-factor redirects).
- HTML responses are parsed with `lxml.etree.HTML()` + XPath expressions.
- Captcha method is configurable via `CAPTCHA_METHOD` env var (`tesseract`, `anticap`, `chaojiying`).
- Session files (`.sep_session.json`, `captcha.png`) are gitignored runtime artifacts.

## Requirements

Python >= 3.11. Key deps: httpx, fastapi, uvicorn, click, pydantic, loguru, cryptography, pillow, lxml, pytesseract. Ruff configured with `line-length = 100`.
