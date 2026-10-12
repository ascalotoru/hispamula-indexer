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
- Detail: `GET /?title=<id>`. eD2k links are login-gated and listed as groups (`table.T2`). Groups come in two shapes:
  - **Modernos**: checkboxes `elink_<group>_<i>` + button `DownloadSelected(<group>, <count>)`. Fetch links in a single batch with `code='1'*count`.
  - **Legacy** (publicaciones antiguas): each row is a `javascript:Download(<group>,'<code>')` link, no checkboxes. Must be fetched **per row** with its own `code`; `_parse_group` marks them with `code` set (None = batch). Do not skip them or their files are lost.
- Fetch links: `GET /ajax/download.php?id=<group>&code=<mask>` → `<textarea id="ELINKSLIST">` with one `ed2k://|file|NAME|SIZE|HASH|/` per line. `code` is a bitmask string ('1' at position *i* = select checkbox *i*).
- Correlate rows ↔ ed2k by **index** (row filename = display name; ed2k `NAME` is dotted). Do not match by name.

## Auth

- Login = `HSLOGIN` cookie = `base64(user:pass)`, sent as `Cookie: HSLOGIN=...`; or POST `/` with `username`/`password`/`login=Iniciar`.
- `HISPAMULA_USER` must be the site **handle**, not the registration email. Email logs in as anonymous (`x-hm-user: ???`). Verify auth via the `x-hm-user` response header.
- Local config in `.env` (gitignored): `HISPAMULA_USER`, `HISPAMULA_PASSWORD`.

## Torznab routes

- Served at `/`, `/api`, and `/api/api` (Prowlarr appends `/api` to the base URL). Endpoints: `t=caps`, `t=search`, `t=movie`, `t=tvsearch`.
- Every item MUST include `<pubDate>` — Prowlarr rejects feeds without it.
- Every item MUST include the Newznab category (parent + subcategories by quality, see `torznab_subcategories` in `app/hispamula.py`) via `<category>` elements and `torznab:attr name="category"`.
- Every item's `<enclosure>` is an **aMulerr magnet** (`to_magnet` in `app/torznab.py`: `magnet:?xt=urn:btih:<base32(ed2k_hash+4 ceros)>&dn=&xl=&tr=http://amulerr`) with `type="application/x-bittorrent"`. Radarr discards `application/x-ed2k` enclosures, and the aMulerr qBittorrent download client only accepts this magnet format (not raw `ed2k://`).
- Every item MUST also set `<torznab:attr name="size">` — the *arr ignore the `<size>` element alone.
- The RSS sync (the *arr query **without `q`**) is capped to `HISPAMULA_RSS_MAX_RESULTS` (default 10). Without it, the cold front-page scrape (N+1, ~100 s) exceeds the *arr ~100 s indexer timeout and the indexer gets disabled.

## Security (repo is PUBLIC)

- Never commit secrets or personal data. `.env` is gitignored.
- Test fixtures are scraped HTML; when regenerating, strip all user info (usernames, gravatar hashes, emails). A prior commit leaked them and had to be purged.

## Deploy

- CI (`.github/workflows/build.yaml`) runs tests then builds+pushes the image to GHCR: `latest` on push to `master`, semver tags `X.Y.Z`/`X.Y` on tag `v*`.

## Releases

- La única fuente de verdad de la versión es `__version__` en `app/__init__.py` (en una línea anotada con `# x-release-please-version`, que release-please usa para actualizarla); el caps de torznab la expone en `appversion`/`version`.
- `release-please` (`.github/workflows/release.yaml`) mantiene un PR de release (`release-please/branches/master → master`) que acumula los commits convencionales desde el último release.
- Para publicar: fusionar ese PR. Al fusionarlo se sube `__version__`, se regenera `CHANGELOG.md`, se crea el tag `vX.Y.Z` (bump: `feat:` → minor, `fix:` → patch, `BREAKING CHANGE` → major) y el Release de GitHub.
- Al fusionar el PR de release, `release.yaml` dispara `build.yaml` (por `workflow_dispatch`, exento de la regla anti-recursión de GitHub) sobre el tag creado, que construye la imagen con etiqueta semver (`X.Y.Z`, `X.Y`). Tags `v*` pusheados manualmente también disparan el build. En push a `master` solo se sube `latest` (dev).
- Bootstrap: `.release-please-manifest.json` arranca en `0.0.0`; la estrategia `simple` fija la primera release en `1.0.0`.

## Version parity

- Python pinned to 3.12.9 in `.python-version`, `Dockerfile`, and CI — keep all three in sync.
- `lxml` pinned 6.1.3 (6.x required for Python 3.14 wheels; 5.3.0 has none).

## Commits

- Commits are grouped **by functionality**: one logical change per commit (feat/fix/docs/chore), following conventional-commit prefixes (e.g. `feat:`, `fix:`, `docs:`, `chore:`, `test:`).
- Do NOT mix unrelated functionalities in the same commit. If several changes are in the working tree, split them into separate commits (stage by hunks with `git add -p`).
- Messages in Spanish, imperative, summarizing the change (`feat: exponer calidad en el feed`, `fix: categorías por género`).
