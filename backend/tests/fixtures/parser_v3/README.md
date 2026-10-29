# Parser v3 regression fixtures

`team8-reference.xlsm` is an unchanged, user-supplied engineering workbook, originally named `Mass Balance Team 8.xlsm`. It is retained for private project regression testing, not as a validated industrial design. VBA is not executed. SHA-256: `f2d297f62d8b5a61bca04de35546a9f722970b2965504bb73fec1edaf80f48b2`. The separately named `(1)` revision was not available.

Other files are synthetic fixtures generated and retained by `test_stream_parser_v3.py`: mixed regions, merged headers, alternate IDs, missing descriptions/units/components, scoped cases, conflicts, hidden data, formula caches and dated formula results. `medium-500.xlsx` is a fixed 500-stream performance fixture. The expectations are independently specified in tests; outputs are not used as their own numerical oracle. Original user workbooks are never rewritten by the tests.

Run from backend: `.venv/bin/python -m pytest tests/test_stream_parser_v3.py`.
