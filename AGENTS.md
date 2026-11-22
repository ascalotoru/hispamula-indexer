# AGENTS.md

Torznab indexer for hispamula.org (eMule/eD2k links). Python 3.12 + FastAPI. Serves a Newznab/Torznab XML feed so Prowlarr/Jackett/*arr can search hispamula and hand `ed2k://` links to aMule.

## Layout

- `app/main.py` — FastAPI routes (torznab endpoints + `/healthz`, `/status`). Entrypoint: `uvicorn app.main:app`.
- `app/hispamula.py` — scraping (search, detail, ed2k extraction, `novedades` = atom.xml parsing) + dataclasses.
- `app/session.py` — httpx client, auth cookie, request throttling.
- `app/torznab.py` — caps + RSS item XML builders.
- `app/cache.py` — in-memory, thread-safe TTL cache (searches and details).
- `app/config.py` — all settings via `HISPAMULA_*` env vars.
- `tests/` — pytest; `fixtures/*` are real scraped pages/feed. Tests never hit the network (`FakeSession` in `conftest.py`).

## Commands

- Install: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` (pyenv 3.12.9 via `.python-version`).
- Run: `.venv/bin/uvicorn app.main:app --reload --port 8080`
- Test: `.venv/bin/python -m pytest` · single file: `.venv/bin/python -m pytest tests/test_torznab.py`
- `pytest.ini` sets `pythonpath=.` and `testpaths=tests`. No lint/typecheck/formatter configured.

## Scraping flow (non-obvious)

- Search: `GET /?view=search&q=<query>` → results in `tr.T1`, pagination `&page=N`.
- Detail: `GET /?title=<id>`. eD2k links are login-gated and listed as groups (`table.T2`). Groups come in two shapes:
  - **Modern**: checkboxes `elink_<group>_<i>` + button `DownloadSelected(<group>, <count>)`. Fetch links in a single batch with `code='1'*count`.
  - **Legacy** (old publications): each row is a `javascript:Download(<group>,'<code>')` link, no checkboxes. Must be fetched **per row** with its own `code`; `_parse_group` marks them with `code` set (None = batch). Do not skip them or their files are lost.
- Fetch links: `GET /ajax/download.php?id=<group>&code=<mask>` → `<textarea id="ELINKSLIST">` with one `ed2k://|file|NAME|SIZE|HASH|/` per line. `code` is a bitmask string ('1' at position *i* = select checkbox *i*).
- Correlate rows ↔ ed2k by **index** (row filename = display name; ed2k `NAME` is dotted). Do not match by name.
- Recent releases: `GET /atom.xml` (Atom) lists recent titles with their `title_id`; `novedades()` parses it. Cheap alternative to the front page, used by `/status` to know what is cached.

## Auth

- Login = `HSLOGIN` cookie = `base64(user:pass)`, sent as `Cookie: HSLOGIN=...`; or POST `/` with `username`/`password`/`login=Iniciar`.
- `HISPAMULA_USER` must be the site **handle**, not the registration email. Email logs in as anonymous (`x-hm-user: ???`). Verify auth via the `x-hm-user` response header.
- Local config in `.env` (gitignored): `HISPAMULA_USER`, `HISPAMULA_PASSWORD`.

## Torznab routes

- Served at `/`, `/api`, and `/api/api` (Prowlarr appends `/api` to the base URL). Endpoints: `t=caps`, `t=search`, `t=movie`, `t=tvsearch`.
- Every item MUST include `<pubDate>` — Prowlarr rejects feeds without it.
- Movie item titles MUST carry the year from the title page (`Nombre (2020) [group label]`, year before the bracket). Radarr rejects year-less names as `Unable to parse release`. Only video extensions get the year: appending it to a `.srt` made Radarr treat the subtitle as a valid release.
- Every item MUST include the Newznab category (parent + subcategories by quality, see `torznab_subcategories` in `app/hispamula.py`) via `<category>` elements and `torznab:attr name="category"`.
- Every item's `<enclosure>` is an **aMulerr magnet** (`to_magnet` in `app/torznab.py`: `magnet:?xt=urn:btih:<base32(ed2k_hash+4 zero bytes)>&dn=&xl=&tr=http://amulerr`) with `type="application/x-bittorrent"`. Radarr discards `application/x-ed2k` enclosures, and the aMulerr qBittorrent download client only accepts this magnet format (not raw `ed2k://`).
- Every item MUST also set `<torznab:attr name="size">` — the *arr ignore the `<size>` element alone.
- The RSS sync (the *arr query **without `q`**) is capped to `HISPAMULA_RSS_MAX_RESULTS` (default 10). Without it, the cold front-page scrape (N+1, ~100 s) exceeds the *arr ~100 s indexer timeout and the indexer gets disabled.
- Non-Torznab routes: `GET /healthz` (liveness) and `GET /status` (cache state; `caliente` = `atom.xml` recent releases already cached). Documented in `README.md`.

## Security (repo is PUBLIC)

- Never commit secrets or personal data. `.env` is gitignored.
- Test fixtures are scraped HTML; when regenerating, strip all user info (usernames, gravatar hashes, emails). A prior commit leaked them and had to be purged.

## Deploy

- CI (`.github/workflows/build.yaml`) runs tests then builds+pushes the image to GHCR: `latest` on push to `master`, semver tags `X.Y.Z`/`X.Y` on tag `v*`.

## Releases

- The single source of truth for the version is `__version__` in `app/__init__.py` (on a line annotated with `# x-release-please-version`, which release-please uses to update it); the torznab caps expose it as `appversion`/`version`.
- `release-please` (`.github/workflows/release.yaml`) maintains a release PR (`release-please/branches/master → master`) that accumulates the conventional commits since the last release.
- To publish: merge that PR. Merging bumps `__version__`, regenerates `CHANGELOG.md`, creates the `vX.Y.Z` tag (bump: `feat:` → minor, `fix:` → patch, `BREAKING CHANGE` → major) and the GitHub Release.
- When the release PR is merged, `release.yaml` triggers `build.yaml` (via `workflow_dispatch`, exempt from GitHub's anti-recursion rule) on the created tag, which builds the image tagged with semver (`X.Y.Z`, `X.Y`). Manually pushed `v*` tags also trigger the build. On push to `master` only `latest` (dev) is pushed.
- Bootstrap: `.release-please-manifest.json` starts at `0.0.0`; the `simple` strategy sets the first release to `1.0.0`.

## Version parity

- Python pinned to 3.12.9 in `.python-version`, `Dockerfile`, and CI — keep all three in sync.
- `lxml` pinned 6.1.3 (6.x required for Python 3.14 wheels; 5.3.0 has none).

## Docs

- If a change affects routes, env vars, scraping flow, or integration, update the corresponding docs (`README.md`, this `AGENTS.md`) in the same change.
- If the change is docs-only, use a separate `docs:` commit.

## Commits

- Commits are grouped **by functionality**: one logical change per commit (feat/fix/docs/chore), following conventional-commit prefixes (e.g. `feat:`, `fix:`, `docs:`, `chore:`, `test:`).
- Do NOT mix unrelated functionalities in the same commit. If several changes are in the working tree, split them into separate commits (stage by hunks with `git add -p`).
- Messages in Spanish, imperative, summarizing the change (`feat: exponer calidad en el feed`, `fix: categorías por género`).
