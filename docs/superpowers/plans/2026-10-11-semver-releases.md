# Releases semánticos con GitHub Releases — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publicar releases semánticos de GitHub con tag `vX.Y.Z`, imagen `X.Y.Z` en GHCR y versión real expuesta en el caps de torznab, con cadencia controlada por PR de release.

**Architecture:** `release-please` (modo PR) deriva el bump de los commits convencionales y, al fusionar su PR, sube `__version__` en `app/__init__.py`, regenera `CHANGELOG.md`, crea el tag y el Release. `build.yaml` construye `latest` en cada push a `master` y la imagen semver en cada tag `v*`.

**Tech Stack:** GitHub Actions (`googleapis/release-please-action@v4`, `docker/metadata-action@v5`), Python 3.12.9, FastAPI.

**Spec:** `docs/superpowers/specs/2026-10-11-semver-releases-design.md`

## Global Constraints

- Fuente de verdad de la versión: `app/__init__.py` → `__version__ = "0.1.0"` (inicial).
- Manifest de release-please arranca en `0.0.0`; primera release = `0.1.0`.
- Commits con prefijo convencional, mensajes en español, imperativo (`feat:`, `fix:`, `ci:`, `docs:`), un cambio lógico por commit.
- Imagen: `ghcr.io/ascalotoru/hispamula-indexer`.
- `latest` = último `master` (dev); tags `X.Y.Z` y `X.Y` = release.
- Nada de secretos en el repo.

## Review Focus (riesgos que no cubren los tests)

1. **Drift de versión**: `__version__` podría no coincidir con el release. → el config de release-please incluye `extra-files` para bump `app/__init__.py`, y el test del caps pina que el XML usa `__version__` (no `"0.1"` hardcodeado).
2. **Permisos insuficientes**: release-please fallaría creando PR/tag/release. → `permissions: contents: write, pull-requests: write` en `release.yaml`.
3. **Bootstrap de versión**: primera release en `0.1.0` tras el `feat:` del setup (manifest `0.0.0`).
4. **Imagen sin etiquetar en release**: si el trigger de tag no funciona, no hay imagen semver. → verificado en el primer release con `type=semver`.
5. **Flux sigue a `latest`**: hasta migrar el repo gitops a rango semver, los releases no se despliegan solos. → fuera de este repo (seguimiento anotado).

---

### Task 1: Exponer la versión real en el caps

**Files:**
- Modify: `app/__init__.py`
- Modify: `app/torznab.py:13-18`
- Test: `tests/test_torznab.py`

**Interfaces:**
- Produces: `app.__version__` (str, `"0.1.0"`), usado por `capabilities()`.

- [ ] **Step 1: Escribir el test que falla**

En `tests/test_torznab.py` (añadir import y test):

```python
from app import __version__
from app.hispamula import Ed2kFile, torznab_subcategories
from app.torznab import capabilities, feed


def test_caps_exposes_package_version():
    xml = capabilities()
    assert f'appversion="{__version__}"' in xml
    assert f'version="{__version__}"' in xml
```

- [ ] **Step 2: Verificar que falla**

Run: `.venv/bin/python -m pytest tests/test_torznab.py::test_caps_exposes_package_version -v`
Expected: FAIL (`ImportError: cannot import name '__version__'`).

- [ ] **Step 3: Implementar `__version__`**

En `app/__init__.py` (hoy vacío), una sola línea:

```python
__version__ = "0.1.0"
```

En `app/torznab.py`, añadir `from . import __version__` junto a los otros imports, y en `capabilities()` cambiar la línea del `<server>` para usar la variable:

```python
f'  <server appversion="{__version__}" version="{__version__}" title="Hispamula" '
```

(el resto de literales adyacentes se mantienen igual; Python permite mezclar f-string con strings normales en la concatenación implícita).

- [ ] **Step 4: Verificar que pasa**

Run: `.venv/bin/python -m pytest tests/test_torznab.py -v`
Expected: PASS (todos los tests del archivo).

- [ ] **Step 5: Commit**

```bash
git add app/__init__.py app/torznab.py tests/test_torznab.py
git commit -m "feat: exponer versión real en el caps"
```

---

### Task 2: Workflow de release con release-please

**Files:**
- Create: `.github/workflows/release.yaml`
- Create: `.release-please-config.json`
- Create: `.release-please-manifest.json`

**Interfaces:**
- Produce: PR automático `release-please/branches/master → master`; al fusionarlo crea tag `vX.Y.Z`, Release de GitHub y bump de `app/__init__.py` + `CHANGELOG.md`.

- [ ] **Step 1: Crear `.release-please-manifest.json`**

```json
{
  ".": "0.0.0"
}
```

- [ ] **Step 2: Crear `.release-please-config.json`**

```json
{
  "release-type": "simple",
  "extra-files": [
    {
      "type": "generic",
      "path": "app/__init__.py",
      "pattern": "__version__ = \"([^\"]*)\""
    }
  ]
}
```

- [ ] **Step 3: Crear `.github/workflows/release.yaml`**

```yaml
name: release

on:
  push:
    branches: [master]

permissions:
  contents: write
  pull-requests: write

jobs:
  release-please:
    runs-on: ubuntu-latest
    steps:
      - uses: googleapis/release-please-action@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
```

- [ ] **Step 4: Validar sintaxis YAML/JSON**

Run: `python -c "import json; json.load(open('.release-please-config.json')); json.load(open('.release-please-manifest.json'))"`
Y revisar que el YAML no tenga tabuladores (espacios a 2).

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/release.yaml .release-please-config.json .release-please-manifest.json
git commit -m "ci: automatizar releases semánticos con release-please"
```

---

### Task 3: Etiquetar la imagen con versión semántica

**Files:**
- Modify: `.github/workflows/build.yaml`

**Interfaces:**
- Produce: imagen `latest` en push a `master`; imagen `X.Y.Z` y `X.Y` en push de tag `v*`.

- [ ] **Step 1: Añadir el trigger de tags**

En `build.yaml`, cambiar el bloque `on.push` para incluir `tags`:

```yaml
on:
  push:
    branches: [master]
    tags: ['v*']
  workflow_dispatch:
```

- [ ] **Step 2: Reemplazar el bloque `tags:` del metadata-action**

Sustituir `type=sha,prefix=` y `type=raw,value=latest` por:

```yaml
          tags: |
            type=raw,value=latest,enable=${{ github.ref_type == 'branch' }}
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/build.yaml
git commit -m "ci: etiquetar imagen con versión semántica en releases"
```

---

### Task 4: Documentar el flujo de release

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: Añadir la sección "Releases" a `AGENTS.md`**

Documentar: la versión vive en `app/__init__.py`; release-please mantiene un PR de release que acumula commits convencionales; para publicar se fusiona ese PR, lo que sube `__version__`, crea el tag `vX.Y.Z` y el Release; el tag dispara la imagen `X.Y.Z`; Flux (en el repo gitops) debe seguir un rango semver.

- [ ] **Step 2: Commit**

```bash
git add AGENTS.md
git commit -m "docs: documentar flujo de releases"
```

---

## Seguimiento (fuera de este repo)

Migrar en `ascalotoru/k3s-asiercl-flux` (namespace `servarr`) la referencia de la imagen de `latest` a un rango semver (p. ej. `1.x`), para que los releases se desplieguen automáticamente.
