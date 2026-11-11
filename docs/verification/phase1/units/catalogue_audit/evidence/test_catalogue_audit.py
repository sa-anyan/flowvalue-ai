"""Targeted verification tests; no production integration or network calls."""
import runpy
from pathlib import Path
import pytest
AUDIT = runpy.run_path(str(Path(__file__).with_name('audit_catalogue.py')))
@pytest.mark.parametrize('case', AUDIT['RESULTS'], ids=lambda case: case['check'])
def test_independent_catalogue_check(case):
    assert case['passed'], case['detail']
