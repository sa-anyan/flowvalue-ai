"""Test-only upstream CostCorrelationDB, commit 9d769ad1583794401e4c441272ba7cccc46aff75.
MIT Copyright (c) 2025 Panji Tamarona; full notice in index/LICENSE_NOTICE.md.
Exact class extracted by AST; no numerical implementation edits. No live imports.
"""
import numpy as np
import pandas as pd
COST_DB_DF = None
class CostCorrelationDB:
    """
    Database interface for equipment cost correlations.

    Manages cost estimation correlations for equipment based on size/capacity
    parameters. Supports multiple correlation forms (offset power-law,
    log-log quadratic, ln-ln quartic, power-sizing, 2-var power-law) and
    handles equipment parallelization when capacity limits are exceeded.

    Attributes
    ----------
    df : pd.DataFrame
        Cost correlation data with columns: key, category, type, form,
        s_lower, s_upper, s2_lower, s2_upper, upper_parallel, a, b, n, n2,
        k1, k2, k3, k4, k5, s0, c0, f, cost_year.
    """

    def __init__(self, df=COST_DB_DF):
        """
        Initialize database with cost correlation DataFrame.

        Normalizes column names to lowercase and converts numeric columns.

        Parameters
        ----------
        df : pd.DataFrame
            Cost correlation data. Defaults to the bundled CSV database.
            The input is not modified; normalization happens on a copy.
        """
        # Never normalize in place: df defaults to the shared
        # module-level database, and a user-supplied frame must not be
        # mutated as a construction side effect
        df = df.copy()
        df.columns = [c.strip().lower() for c in df.columns]
        for col in [
            "s_lower",
            "s_upper",
            "s2_lower",
            "s2_upper",
            "upper_parallel",
            "a",
            "b",
            "n",
            "n2",
            "s0",
            "c0",
            "f",
            "cost_year",
        ]:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col], errors="coerce"
                )
        df["form"] = df["form"].str.lower()
        self.df = df

    def evaluate(self, key: str, s: float, s2: float | None = None):
        """
        Calculate purchased equipment cost based on correlation key and size.

        Parameters
        ----------
        key : str
            Unique identifier for the cost correlation.
        s : float
            Equipment size/capacity parameter.
        s2 : float | None, optional
            Second size/capacity parameter, required by two-parameter
            correlation forms such as ``"2-var power-law"``. Validated
            against ``s2_lower``/``s2_upper`` but never parallelized.
            Default is None.

        Returns
        -------
        tuple[float, int, int]
            (total_cost, number_of_units, cost_year).

        Raises
        ------
        KeyError
            If correlation key not found in database.
        ValueError
            If size (or ``s2``) is outside its valid bounds, the
            correlation form is unsupported, or the form requires ``s2``
            and none was given.
        """
        row = self.df.loc[self.df["key"] == key]
        if row.empty:
            raise KeyError(
                f"Correlation key not found in CSV: {key}"
            )
        r = row.iloc[0].to_dict()

        s_lower = r.get("s_lower")
        s_upper = r.get("s_upper")
        cap = (
            r.get("upper_parallel")
            if pd.notna(r.get("upper_parallel"))
            else s_upper
        )

        if pd.notna(s_lower) and s < s_lower:
            raise ValueError(
                f"s={s} below lower bound {s_lower} for key '{key}'"
            )

        if s2 is not None:
            s2_lower = r.get("s2_lower")
            s2_upper = r.get("s2_upper")
            if pd.notna(s2_lower) and s2 < s2_lower:
                raise ValueError(
                    f"s2={s2} below lower bound {s2_lower} for key '{key}'"
                )
            if pd.notna(s2_upper) and s2 > s2_upper:
                raise ValueError(
                    f"s2={s2} above upper bound {s2_upper} for key '{key}'"
                )

        # Split a size above the unit capacity into equal parallel units
        units, s_adj = 1, s
        if pd.notna(cap) and s > cap:
            units = int(np.ceil(s / cap))
            s_adj = s / units
        form = r.get("form", "linear")
        year = int(r["cost_year"])

        if form == "offset power-law":
            a, b, n = r["a"], r["b"], r["n"]
            ce = a + b * (s_adj**n)

        elif form == "exponential":
            a, b = r["a"], r["b"]
            ce = a * np.exp(b * s_adj)

        elif form in ("log-log quadratic", "ln-ln quadratic"):
            # log(Ce) is a polynomial (up to 4th order) in log(S), base 10
            # or e
            log, unlog = (
                (np.log10, lambda x: 10**x) if form == "log-log quadratic"
                else (np.log, np.exp)
            )
            K1, K2, K3 = r["k1"], r["k2"], r["k3"]
            K4 = r.get("k4") if pd.notna(r.get("k4")) else 0.0
            K5 = r.get("k5") if pd.notna(r.get("k5")) else 0.0

            logS = log(s_adj)
            ce = unlog(
                K1
                + K2 * logS
                + K3 * (logS**2)
                + K4 * (logS**3)
                + K5 * (logS**4)
            )

        elif form == "power-sizing":
            C0, S0, f = r["c0"], r["s0"], r["f"]
            ce = C0 * (s_adj / S0) ** f

        elif form == "2-var power-law":
            if s2 is None:
                raise ValueError(
                    f"Correlation '{key}' has form '2-var "
                    f"power-law' and requires a second size parameter "
                    f"(s2)."
                )
            a, b, n1, n2 = r["a"], r["b"], r["n"], r["n2"]
            ce = a + b * (s_adj**n1) * (s2**n2)

        else:
            raise ValueError(
                f"Unsupported form '{form}' for key '{key}'"
            )

        purchased = ce * units
        return float(purchased), int(units), year

    def key_for_category_type(
        self, eq_category: str, type: str | None
    ):
        """
        Look up correlation key by equipment category and optional type.

        Parameters
        ----------
        eq_category : str
            Equipment category name.
        type : str | None
            Equipment sub-type (optional).

        Returns
        -------
        str | None
            Correlation key if found, None otherwise.
        """
        t = eq_category.lower()
        st = type.lower() if type else ""
        df = self.df

        if "category" not in df.columns:
            return None

        cand = df[df["category"].str.lower() == t]
        if "type" in df.columns:
            cand = cand[
                cand["type"].fillna("").str.lower() == st
            ]

        if cand.empty:
            return None

        return cand.iloc[0]["key"]

    def default_material_for_key(self, key: str) -> str | None:
        """
        Look up the cost basis's default construction material for a key.

        Parameters
        ----------
        key : str
            Correlation key.

        Returns
        -------
        str | None
            The ``default material`` value for the row, or None if the
            key is not found, the column is absent, or the value is
            unset (e.g. ``"n.a."``).
        """
        if "default material" not in self.df.columns:
            return None
        row = self.df.loc[self.df["key"] == key]
        if row.empty:
            return None
        val = row.iloc[0]["default material"]
        if pd.isna(val) or str(val).strip().lower() == "n.a.":
            return None
        return str(val).strip()
