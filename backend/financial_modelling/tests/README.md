# Financial modelling tests

Canonical automated tests live in `backend/tests/test_financial_modelling.py` to
match repository-wide unittest discovery. Run from repository root:

```sh
python3 -m unittest backend.tests.test_financial_modelling -v
```

Cases use independently specified synthetic inputs, Garrett's supported rounded
cash-flow table, and canonical upstream engine outputs. No original Excel formulas
or expected outputs are used. Optional OpenPyTEA 3.2.1 NPV comparison evidence is
separate and does not add a runtime dependency. See the package README for methods,
conventions, source discrepancies and remaining industrial-validation limits.
