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

- No se implementa el cambio del repo gitops (`<redacted>`); queda como
  seguimiento. Hasta migrar Flux a un rango semver, los releases no se
  despliegan solos.
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
  usa en `capabilities()`.
- **Bootstrap:** `.release-please-manifest.json` arranca en `0.0.0` (no hay
  release todavía). El commit `feat:` del setup hace el bump minor a `0.1.0`, de
  modo que la primera release es `0.1.0` y no se salta ningún número.
- **Imagen:** en push a `master` → `latest`; en push de tag `v*` → `X.Y.Z` y
  `X.Y` vía `type=semver`. Se elimina el tag `sha` (el commit siempre es
  referenciable).

## Comportamiento de la versión

- Antes de la primera release: `app/__init__.py` dice `0.1.0` y el manifest dice
  `0.0.0`.
- Al fusionar el PR de release de release-please: el manifest pasa a `0.1.0`, se
  escribe `__version__ = "0.1.0"`, se crea el tag `v0.1.0` y el Release.
- De ahí en adelante: `feat:` → minor, `fix:` → patch, `BREAKING CHANGE` → major.
