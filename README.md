# hispamula-indexer

A [Torznab](https://torznab.readthedocs.io/)/Newznab indexer for [hispamula.org](https://www.hispamula.org/) — a Spanish catalog of movies, series and documentaries shared as eMule/eD2k links. It scrapes the site and exposes a searchable XML feed so [Prowlarr](https://prowlarr.com/), [Jackett](https://github.com/Jackett/Jackett) and the *arr stack (Sonarr/Radarr/…) can search hispamula and hand `ed2k://` links to an eMule client (e.g. [aMule](https://www.amule.org/)).

## Features

- **Torznab API** — `caps`, `search`, `movie`, `tvsearch` endpoints.
- **Real eD2k extraction** — fetches the actual `ed2k://` links (hash + size), not just titles.
- **Authenticated** — logs in to hispamula to reach login-gated links.
- **Categories** — maps Película/Documental → Movies (2000), Serie/Docuserie → TV (5000).
- **Rate-limited scraping** — configurable delay + per-title caching.
- **Docker + CI** — builds and publishes a container image to GHCR.

## How it works

```
*arr ──query──▶ Prowlarr/Jackett ──Torznab──▶ hispamula-indexer ──HTTP──▶ hispamula.org
  ▲                                                              │
  └──────────── ed2k:// link ──▶ download client (aMule) ◀───────┘
```

1. The indexer receives a Torznab search request (`q`, optional `season`/`ep`).
2. It searches hispamula (`/?view=search&q=…`) and parses the result list.
3. For each result it fetches the title page and extracts the eD2k groups.
4. It downloads the actual link list and returns one Torznab `<item>` per `ed2k://` file.
5. The *arr app hands the `ed2k://` URL to its download client (aMule).

## Requirements

- Python 3.12
- A hispamula.org account (free registration). eD2k links are only visible when logged in.

## Setup (local)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env
# edit .env: set HISPAMULA_USER and HISPAMULA_PASSWORD

.venv/bin/uvicorn app.main:app --reload --port 8080
```

> **Important:** `HISPAMULA_USER` is your hispamula **handle** (login name), **not** your registration email. The email logs in as anonymous.

## Docker

```bash
docker build -t hispamula-indexer .
docker run --rm -p 8080:8080 \
  -e HISPAMULA_USER=your_handle \
  -e HISPAMULA_PASSWORD=your_password \
  hispamula-indexer
```

## Integrate with Prowlarr / Jackett

Add a **Generic Torznab** indexer pointing to the service. The API is served at `/`, `/api` and `/api/api`.

- **Prowlarr** appends `/api` to the base URL, so set the base URL to `http://<host>:8080` (no `/api`). Both forms work.
- **Jackett** (custom Torznab) — use the full URL `http://<host>:8080/api`.

Point your *arr app's download client at your eMule bridge (e.g. aMule / amulerr), which accepts the `ed2k://` URLs returned by the indexer.

## Configuration

All settings are environment variables (`HISPAMULA_*`), read by `app/config.py`.

| Variable                  | Default                      | Description                                        |
| ------------------------- | ---------------------------- | -------------------------------------------------- |
| `HISPAMULA_USER`          | —                            | hispamula handle (required for gated links)        |
| `HISPAMULA_PASSWORD`      | —                            | hispamula password                                 |
| `HISPAMULA_BASE_URL`      | `https://www.hispamula.org`  | site base URL                                      |
| `HISPAMULA_REQUEST_DELAY` | `1.0`                        | seconds between requests                           |
| `HISPAMULA_CACHE_TTL`     | `600`                        | cache lifetime (seconds) for title/link pages      |
| `HISPAMULA_TIMEOUT`       | `30.0`                       | HTTP timeout (seconds)                             |
| `HISPAMULA_MAX_RESULTS`   | `25`                         | max titles processed per search                    |
| `HISPAMULA_USER_AGENT`    | `hispamula-indexer/0.1`      | User-Agent header                                  |

## Development

```bash
.venv/bin/python -m pytest                 # all tests
.venv/bin/python -m pytest tests/test_torznab.py   # single file
```

Tests run offline against fixtures in `tests/fixtures/` (real scraped HTML) and never hit the network. There is no linter/formatter/typechecker configured.

## License

[Apache License 2.0](LICENSE).

## Disclaimer

This project is **not affiliated with hispamula.org**. It is an unofficial scraper built for personal use. Only download content you have the legal right to, and respect hispamula.org's terms of service and any applicable copyright law.
