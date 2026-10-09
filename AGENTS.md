# AGENTS.md

Torznab indexer for hispamula.org (eMule/eD2k links). Python 3.12 + FastAPI. Serves a Newznab/Torznab XML feed so Prowlarr/Jackett/*arr can search hispamula and hand `ed2k://` links to aMule.

## Layout

- `app/main.py` — FastAPI routes (torznab endpoints). Entrypoint: `uvicorn app.main:app`.
- `app/hispamula.py` — scraping (search, detail, ed2k extraction) + dataclasses.
- `app/session.py` — httpx client, auth cookie, request throttling.
- `app/torznab.py` — caps + RSS item XML builders.
- `app/config.py` — all settings via `HISPAMULA_*` env vars.
- `tests/` — pytest; `fixtures/*.html` are real scraped pages. Tests never hit the network (`FakeSession` in `conftest.py`).

## Commands

- Install: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` (pyenv 3.12.9 via `.python-version`).
- Run: `.venv/bin/uvicorn app.main:app --reload --port 8080`
- Test: `.venv/bin/python -m pytest` · single file: `.venv/bin/python -m pytest tests/test_torznab.py`
- `pytest.ini` sets `pythonpath=.` and `testpaths=tests`. No lint/typecheck/formatter configured.

## Scraping flow (non-obvious)

- Search: `GET /?view=search&q=<query>` → results in `tr.T1`, pagination `&page=N`.
- Detail: `GET /?title=<id>`. eD2k links are login-gated and listed as groups (`table.T2`, checkboxes `elink_<group>_<i>`, button `DownloadSelected(<group>, <count>)`).
- Fetch links: `GET /ajax/download.php?id=<group>&code=<count ones>` → `<textarea id="ELINKSLIST">` with one `ed2k://|file|NAME|SIZE|HASH|/` per line.
- Correlate rows ↔ ed2k by **index** (row filename = display name; ed2k `NAME` is dotted). Do not match by name.

## Auth

- Login = `HSLOGIN` cookie = `base64(user:pass)`, sent as `Cookie: HSLOGIN=...`; or POST `/` with `username`/`password`/`login=Iniciar`.
- `HISPAMULA_USER` must be the site **handle**, not the registration email. Email logs in as anonymous (`x-hm-user: ???`). Verify auth via the `x-hm-user` response header.
- Local config in `.env` (gitignored): `HISPAMULA_USER`, `HISPAMULA_PASSWORD`.

## Torznab routes

- Served at `/`, `/api`, and `/api/api` (Prowlarr appends `/api` to the base URL). Endpoints: `t=caps`, `t=search`, `t=movie`, `t=tvsearch`.
- Every item MUST include `<pubDate>` — Prowlarr rejects feeds without it.

## Security (repo is PUBLIC)

- Never commit secrets or personal data. `.env` is gitignored.
- Test fixtures are scraped HTML; when regenerating, strip all user info (usernames, gravatar hashes, emails). A prior commit leaked them and had to be purged.

## Deploy

- Manifests are NOT in this repo; they live in gitops repo `ascalotoru/k3s-asiercl-flux` under `applications/hispamula-indexer/` (namespace `servarr`, image `ghcr.io/ascalotoru/hispamula-indexer`).
- CI (`.github/workflows/build.yaml`) runs tests then builds+pushes the image to GHCR on push to `master`.

## Version parity

- Python pinned to 3.12.9 in `.python-version`, `Dockerfile`, and CI — keep all three in sync.
- `lxml` pinned 6.1.3 (6.x required for Python 3.14 wheels; 5.3.0 has none).
