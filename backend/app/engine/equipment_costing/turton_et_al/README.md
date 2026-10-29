# Turton et al. equipment modules

Canonical registry: `__init__.py` → `METHODS`. Existing screening coefficients are retained without changes; see `docs/calculation_basis.md` at the repository root for provenance and limitations.

| Equipment | Module | Characteristic size | Range |
|---|---|---|---|
| Fixed-tube shell-and-tube exchanger | [heat_exchangers.py](heat_exchangers.py) | Area, m² | 10–1,000 |
| Vertical vessel shell | [vessels.py](vessels.py) | Volume, m³ | 0.3–520 |
| Centrifugal pump | [pumps.py](pumps.py) | Shaft power, kW | 1–300 |
| Compressor | [compressors.py](compressors.py) | Fluid power, kW | 450–3,000 |

Each module exposes `estimate_base_price(equipment_id, size)` and owns its `CORRELATION` and existing material-factor assumptions. `_common.py` supplies shared arithmetic and the price envelope; it contains no equipment-specific coefficients. Returned prices remain at the declared original index basis, not today’s price. Extrapolation is blocked by the public price function. The compatibility dispatcher retains the prior API.
