# AGENTS.md

## Cursor Cloud specific instructions

This repo is a single Python CLI/library for downloading ERA5 climate data from the
Copernicus Climate Data Store (CDS). There are **no services, servers, ports, or
databases** — it is a batch CLI that builds a request, downloads files, and exits.
The only dependency is `cdsapi` (see `requirements.txt`). Python 3.9+ is required
(source uses `list[str]` / `X | None` typing).

### Running / testing without credentials

- Use `--dry-run` to exercise the full code path (arg parsing + CDS request
  construction + target-file planning) **without network access or credentials**.
  This is the recommended way to validate changes. Example:
  `python3 download_era5_daily.py daily-statistics --variables 2m_temperature --start-year 2020 --end-year 2020 --dry-run`
- Presets: `daily-statistics`, `single-levels`, `land`, `pressure-levels`, `model-levels`
  (see `README.md`). Auxiliary utilities live in `scripts/` and also support `--dry-run`.
- There is a small **unittest suite** in `tests/`. Run it with
  `python3 -m unittest discover -s tests -v` (no CDS credentials required).
  `--dry-run` remains useful for manual end-to-end checks of new CLI options.

### Real downloads (require external credentials)

- A real download needs a `~/.cdsapirc` file (template: `config/cdsapirc.example`)
  containing a valid CDS UID/API key, outbound network to `cds.climate.copernicus.eu`,
  and per-dataset accepted terms on the CDS website. CDS also queues large requests,
  so real downloads can take a long time and are not suitable for quick verification.
- Credentials come from the `~/.cdsapirc` file, **not** environment variables.
