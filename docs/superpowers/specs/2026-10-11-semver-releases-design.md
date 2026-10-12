# Diseño: releases semánticos con GitHub Releases

## Intención

Hasta ahora cada push a `master` construye la imagen y la etiqueta con el short
sha del commit y `latest`. No existe ningún release ni número de versión. Se
quiere un proceso de publicación profesional: versiones semánticas, Releases de
GitHub con notas de cambios, e imagen etiquetada con la versión. La app debe
además reportar su versión real a los clientes (Prowlarr/Jackett) en el caps de
torznab, en vez del `0.1` hardcodeado actual.

## Objetivos

- Releases semánticos de GitHub (`vX.Y.Z`) con changelog autogenerado.
- Cadencia **controlada**: no se publica en cada push, sino cuando se decide.
- Imagen en GHCR etiquetada con la versión (`X.Y.Z` y `X.Y`), además de `latest`
  para builds de desarrollo.
- El caps de torznab expone la versión real de la release.
- Una única fuente de verdad de la versión en el código.

## No objetivos

- No se implementa el despliegue de los releases (los manifiestos viven fuera de
  este repo); queda como seguimiento.
- No se introduce `pyproject.toml`: el proyecto no es un paquete, es un servicio.

## Restricciones

- Mensajes de commit convencionales en español, imperativo, un cambio lógico por
  commit (`AGENTS.md`).
- Python 3.12.9 sin cambios.
- El repo es público: nada de secretos.

## Decisiones

- **Herramienta:** `googleapis/release-please-action@v4`, que funciona en modo
  "release PR" (mantiene un PR que acumula commits convencionales; al fusionarlo
  crea tag + Release + bump). Es la traducción directa de "cadencia controlada";
  el modo por-push sería `semantic-release`.
- **Fuente de versión:** `__version__` en `app/__init__.py`, no `pyproject.toml`.
  Se copia a la imagen (el `Dockerfile` hace `COPY app ./app`) y `torznab.py` lo
  usa en `capabilities()`. La línea lleva la anotación `# x-release-please-version`:
  el updater `Generic` de release-please (vía `extra-files`) funciona con
  anotaciones y no admite regex, así que el marcador es la forma documentada de
  que actualice la versión en un fichero de texto.
- **Bootstrap:** `.release-please-manifest.json` arranca en `0.0.0`. La estrategia
  `simple` usa su versión inicial por defecto (`1.0.0`) para la primera release,
  lo que se aceptó como tal.
- **Imagen:** en push a `master` → `latest`; en push de tag `v*` → `X.Y.Z` y
  `X.Y` vía `type=semver`. Se elimina el tag `sha` (el commit siempre es
  referenciable).

## Comportamiento de la versión

- Antes de la primera release: `app/__init__.py` dice `0.1.0` y el manifest dice
  `0.0.0`.
- Al fusionar el PR de release de release-please: el manifest pasa a `1.0.0`, la
  línea anotada pasa a `__version__ = "1.0.0"`, se crea el tag `v1.0.0` y el
  Release.
- De ahí en adelante: `feat:` → minor, `fix:` → patch, `BREAKING CHANGE` → major.
