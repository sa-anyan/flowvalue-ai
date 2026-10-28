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
