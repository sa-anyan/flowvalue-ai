# Third-party software and licensing notices

FlowValue AI's original code is covered by the [proprietary rights-reservation notice](LICENSE).

## Dependency licence boundaries

The source-code notice does **not** override any licence granted by the authors
of external dependencies. Their respective copyright, attribution, redistribution,
source-disclosure and other conditions continue to apply. A dependency's mere
appearance in this list does **not** establish that a specific licence has been
verified, or grant rights to copy another repository.

The following is an inventory of **declared direct dependencies**, generated from
the repository manifests on 28 October 2026. It is **not** a complete Software Bill
of Materials, a substitute for the exact upstream licence texts, or a legal-compliance
audit. Verify the licence and version of every installed direct and transitive
dependency before redistributing binaries, vendoring source or shipping a
commercial package.

### Frontend runtime — `frontend/package.json`

- `@base-ui/react`
- `@react-three/drei`
- `@react-three/fiber`
- `@supabase/supabase-js`
- `@xyflow/react`
- `class-variance-authority`
- `cn`
- `lucide-react`
- `next`
- `react`
- `react-dom`
- `react-markdown`
- `recharts`
- `shadcn`
- `three`
- `tw-animate-css`

### Frontend development — `frontend/package.json`

- `@tailwindcss/turbopack`
- `@types/node`
- `@types/react`
- `@types/react-dom`
- `@types/three`
- `eslint`
- `eslint-config-next`
- `tailwindcss`
- `typescript`

### Backend runtime — `backend/pyproject.toml`

- `fastapi`
- `uvicorn[standard]`
- `pydantic-settings`
- `python-multipart`
- `pandas`
- `numpy`
- `scipy`
- `openpyxl`
- `xlrd==2.0.2`
- `defusedxml`
- `reportlab>=5.1.0`
- `openai>=3.37.0`
- `openpytea==3.2.1`
- `httpx==0.28.1`

### Backend development — `backend/pyproject.toml`

- `httpx`
- `pypdf>=6.21.2`
- `pytest`
- `ruff`
- `xlwt==1.3.0`

### Isolated BioSTEAM runner

Additional optional dependencies are declared in
[`backend/requirements-biosteam.in`](backend/requirements-biosteam.in).
Their licence terms must also be reviewed if that runner is distributed.

## Where to find exact versions and notices

- JavaScript resolved versions: `frontend/package-lock.json`.
- Python locked versions: `backend/uv.lock`, plus
  `backend/requirements-biosteam.txt` for the isolated runner.
- Authoritative licences: each installed package's licence files, distribution
  metadata and upstream source/release for the **resolved version**.
- Do not copy a dependency's licence text blindly from another version.

When distributing a third-party component, retain any upstream
`LICENSE`, `NOTICE`, copyright headers and other materials required by
that component's own terms. Some licences have obligations beyond attribution.

## External engineering code examined as reference

The public [Mo-Somji/HYSYS-ME-Balance-Formatting](https://github.com/Mo-Somji/HYSYS-ME-Balance-Formatting)
repository has no `LICENSE` file in the examined tree. Its approach and sample
inputs may be studied, but **public availability is not permission to
copy/relicense its code**. The FlowValue HYSYS adapter is documented as an
independent implementation; do not paste external source into it without
explicit permission or a verified licence.

## Scope

These notices concern **source-code licensing**. They are not an End User
Licence Agreement, website Terms of Service, privacy policy, trademark
licence, or guarantee of rights to patents, trademarks or uploaded datasets.

## Garrett review-workbook offline importer (30 October 2026)

The optional offline importer was exercised with bundled **openpyxl 3.1.5**.
Its installed distribution declares the MIT licence; the installed LICENCE.rst
was inspected. The importer calls that library without copying its code. MIT
permits proprietary integration while retaining its copyright/licence notice
when distributing the library. This change adds no runtime dependency and does
not vendor or redistribute openpyxl. Original FlowValue code retains its licence.
User-supplied Garrett workbook/PDF data remain separately sourced reference data;
this notice does not assert ownership of or change rights in those sources.

## Optional financial reference check — OpenPyTEA 3.2.1

The installed OpenPyTEA 3.2.1 distribution and its MIT licence (copyright Panji
Tamarona, 2025) were inspected for the optional development NPV comparison.
The comparison invokes the installed package only; no source is copied or vendored
and no production dependency is added. If distributing that dependency later,
retain its upstream copyright and MIT licence. Original FlowValue financial
calculations remain separately authored proprietary source. The comparison
establishes only a declared-timing numerical reference case, not model equivalence
or adoption of OpenPyTEA's default engineering/economic assumptions.

## Local orchestration runtime (30 October 2026)

The optional API/parser requirements declare FastAPI 0.162.0 (MIT), Uvicorn
0.54.0 (BSD-3-Clause), Pydantic 2.14.1 (MIT), python-multipart 0.0.32
(Apache-2.0), openpyxl 3.1.5 (MIT), xlrd 2.0.2 (its distribution's BSD-style
notices), and defusedxml 0.7.1 (PSF licence). Installed distribution metadata
and licence files were inspected before integration. No library source is vendored.
Retain each distribution's exact licences/notices if distributing it.
The restored local UI uses Next.js 16.4.3 and React/React DOM 19.3.0 (MIT);
TypeScript is Apache-2.0. Their installed licence files were inspected.
Resolved JavaScript dependencies are recorded in frontend/package-lock.json.
Original parser source was selectively recovered from FlowValue's own checkpoint,
with its recovery manifest in backend/ingestion/RECOVERY.json; no third-party
simulator script was copied or executed. This does not change FlowValue's licence.

### Monte Carlo numerical runtime (resolved 2026-11-03)

The optional Monte Carlo runtime uses NumPy 2.5.4 and SciPy 1.18.1. Their installed
`*.dist-info` licence files were inspected: both core projects use BSD-3-Clause,
compatible with using them as dependencies of proprietary FlowValue code. Their
upstream licences, disclaimers and bundled numerical-library notices remain in
the installed wheels/container; they are not replaced by FlowValue's licence.
No upstream source code was copied into the Monte Carlo module. NumPy/SciPy
sampling is used through their public Python APIs.
