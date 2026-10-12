# hispamula-indexer

Un indexador [Torznab](https://torznab.readthedocs.io/)/Newznab para [hispamula.org](https://www.hispamula.org/) — un catálogo en español de películas, series y documentales compartidos como enlaces eMule/eD2k. Scrapea el sitio y expone un feed XML consultable para que [Prowlarr](https://prowlarr.com/), [Jackett](https://github.com/Jackett/Jackett) y el stack *arr (Sonarr/Radarr/…) puedan buscar en hispamula y pasar los enlaces `ed2k://` a un cliente eMule (por ejemplo [aMule](https://www.amule.org/)).

## Características

- **API Torznab** — endpoints `caps`, `search`, `movie`, `tvsearch`.
- **Extracción real de eD2k** — obtiene los enlaces `ed2k://` reales (hash + tamaño), no sólo los títulos.
- **Autenticado** — inicia sesión en hispamula para acceder a los enlaces restringidos.
- **Categorías Newznab** — mapea Película/Documental → Películas (2000) y Serie/Docuserie → TV (5000), con **subcategorías por calidad/formato** (HD, UHD, SD, WEB-DL, BluRay, x265…).
- **Calidad en el feed** — cada `<item>` incluye la calidad del grupo en el título y los `torznab:attr` correspondientes, para que Prowlarr/*arr clasifiquen 1080p frente a UHD 4K.
- **Scraping con límite de peticiones** — retardo configurable + caché TTL (`HISPAMULA_CACHE_TTL`) de búsquedas y fichas (título + enlaces) para evitar re-raspados.
- **Docker + CI** — construye y publica una imagen de contenedor en GHCR.

## Cómo funciona

```
*arr ──consulta──▶ Prowlarr/Jackett ──Torznab──▶ hispamula-indexer ──HTTP──▶ hispamula.org
  ▲                                                                │
  └──────────── enlace ed2k:// ──▶ cliente de descarga (aMule) ◀────┘
```

1. El indexador recibe una petición de búsqueda Torznab (`q`, con `season`/`ep` opcionales).
2. Busca en hispamula (`/?view=search&q=…`) y analiza la lista de resultados.
3. Para cada resultado obtiene la página del título y extrae los grupos de eD2k.
4. Descarga la lista real de enlaces y devuelve un `<item>` de Torznab por cada archivo `ed2k://`, con su categoría/subcategorías Newznab y calidad (resolución, formato, codec).
5. La aplicación *arr entrega la URL `ed2k://` a su cliente de descarga (aMule).

Las búsquedas y las fichas (título + enlaces) se cachean durante `HISPAMULA_CACHE_TTL` segundos. Así, una consulta repetida —por ejemplo el RSS sync periódico de los *arr, que busca sin `q`— se sirve desde la caché sin volver a raspar el sitio, evitando el timeout del cliente.

## Requisitos

- Python 3.12
- Una cuenta de hispamula.org.

## Instalación (local)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env
# edita .env: define HISPAMULA_USER y HISPAMULA_PASSWORD

.venv/bin/uvicorn app.main:app --reload --port 8080
```

## Docker

```bash
docker build -t hispamula-indexer .
docker run --rm -p 8080:8080 \
  -e HISPAMULA_USER=tu_usuario \
  -e HISPAMULA_PASSWORD=tu_contraseña \
  hispamula-indexer
```

## Integración con Prowlarr / Jackett

Añade un indexador **Generic Torznab** apuntando al servicio. La API se sirve en `/`, `/api` y `/api/api`.

- **Prowlarr** añade `/api` a la URL base, así que define la URL base como `http://<host>:8080` (sin `/api`). Ambas formas funcionan.
- **Jackett** (Torznab personalizado) — usa la URL completa `http://<host>:8080/api`.

Configura el cliente de descarga de tu aplicación *arr para que apunte a tu puente eMule (por ejemplo aMule / amulerr), que acepta las URLs `ed2k://` devueltas por el indexador.

## Configuración

Todas las opciones son variables de entorno (`HISPAMULA_*`), leídas por `app/config.py`.

| Variable                  | Por defecto                  | Descripción                                         |
| ------------------------- | ---------------------------- | --------------------------------------------------- |
| `HISPAMULA_USER`          | —                            | usuario de hispamula (necesario para enlaces restringidos) |
| `HISPAMULA_PASSWORD`      | —                            | contraseña de hispamula                             |
| `HISPAMULA_BASE_URL`      | `https://www.hispamula.org`  | URL base del sitio                                  |
| `HISPAMULA_REQUEST_DELAY` | `1.0`                        | segundos entre peticiones                           |
| `HISPAMULA_CACHE_TTL`     | `3600`                       | vida de la caché (segundos) para búsquedas y páginas de título/enlaces |
| `HISPAMULA_TIMEOUT`       | `30.0`                       | tiempo de espera HTTP (segundos)                    |
| `HISPAMULA_MAX_RESULTS`   | `25`                         | máximo de títulos procesados por búsqueda           |
| `HISPAMULA_USER_AGENT`    | `hispamula-indexer/0.1`      | cabecera User-Agent                                 |

## Desarrollo

```bash
.venv/bin/python -m pytest                 # todos los tests
.venv/bin/python -m pytest tests/test_torznab.py   # un solo archivo
```

Los tests se ejecutan sin red contra los fixtures de `tests/fixtures/` (HTML real scrapeado) y nunca acceden a la red. No hay linter/formateador/typechecker configurado.

## Licencia

[Apache License 2.0](LICENSE).

## Aviso legal

Este proyecto **no está afiliado con hispamula.org**. Es un scraper no oficial creado para uso personal. Descarga únicamente contenido sobre el que tengas derecho legal, y respeta los términos de servicio de hispamula.org y la legislación de derechos de autor aplicable.
