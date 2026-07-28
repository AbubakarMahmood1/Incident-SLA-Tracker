# Runtime Dependencies and Licences

## Scope

This inventory records the locked runtime graph exported from `uv.lock` on 2026-07-28:

```bash
uv export --locked --no-dev --no-emit-project --no-header --no-annotate --no-hashes
```

It does not grant a licence for this repository. The repository itself deliberately remains unlicensed, while each dependency remains governed by its upstream terms.

## Locked runtime graph

| Package | Version | Declared licence |
|---|---:|---|
| Alembic | 1.18.5 | MIT |
| annotated-doc | 0.0.5 | MIT |
| annotated-types | 0.8.0 | MIT |
| AnyIO | 4.14.2 | MIT |
| argon2-cffi | 25.1.0 | MIT |
| argon2-cffi-bindings | 25.1.0 | MIT |
| cffi | 2.1.0 | MIT-0 |
| Click | 8.4.2 | BSD-3-Clause |
| Colorama | 0.4.6 | BSD-3-Clause; Windows only |
| cryptography | 49.0.0 | Apache-2.0 OR BSD-3-Clause |
| dnspython | 2.8.0 | ISC |
| email-validator | 2.3.0 | Unlicense |
| FastAPI | 0.140.9 | MIT |
| greenlet | 3.5.4 | MIT AND PSF-2.0 |
| h11 | 0.16.0 | MIT |
| httptools | 0.8.0 | MIT |
| idna | 3.18 | BSD-3-Clause |
| Mako | 1.3.12 | MIT |
| MarkupSafe | 3.0.3 | BSD-3-Clause |
| psycopg | 3.3.4 | LGPL-3.0-only |
| psycopg-binary | 3.3.4 | LGPL-3.0-only |
| pycparser | 3.0 | BSD-3-Clause |
| pydantic | 2.13.4 | MIT |
| pydantic-core | 2.46.4 | MIT |
| pydantic-settings | 2.14.2 | MIT |
| PyJWT | 2.13.0 | MIT |
| python-dotenv | 1.2.2 | BSD-3-Clause |
| python-multipart | 0.0.32 | Apache-2.0 |
| PyYAML | 6.0.3 | MIT |
| SQLAlchemy | 2.0.51 | MIT |
| Starlette | 1.3.1 | BSD-3-Clause |
| typing-extensions | 4.16.0 | PSF-2.0 |
| typing-inspection | 0.4.2 | MIT |
| tzdata | 2026.3 | Apache-2.0; Windows only |
| Uvicorn | 0.51.0 | BSD-3-Clause |
| uvloop | 0.22.1 | MIT; non-Windows CPython |
| watchfiles | 1.2.0 | MIT |
| websockets | 16.1.1 | BSD-3-Clause |

Metadata comes from installed distribution metadata and the platform-conditioned locked export. Upstream licence files remain authoritative if metadata differs.

## Distribution boundary

- No third-party source is vendored in this repository.
- A built image contains installed dependency artifacts and must preserve applicable upstream notices.
- `psycopg` and `psycopg-binary` are LGPL-3.0-only; anyone distributing an image or binary bundle must review and satisfy the applicable LGPL obligations.
- Platform-conditioned packages mean the exact installed subset differs between Linux and Windows while remaining locked.
- Dependency vulnerability and licence results must be rechecked when `uv.lock` changes.

This inventory is an engineering record, not legal advice.
