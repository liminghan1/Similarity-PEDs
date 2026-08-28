"""Disproportionality-analysis statistics (Reporting Odds Ratio) for FAERS signal detection.

Implements the 2x2 contingency-table ROR calculation specified in the project brief (Sec. 11):

                 Event E       Other Events
    Drug D           a              b
    Other Drugs      c              d

    ROR = (a*d) / (b*c)
    logROR = log(ROR)
    SE(logROR) = sqrt(1/a + 1/b + 1/c + 1/d)
    95% CI = exp(logROR +/- 1.96 * SE)

This module computes signal statistics only. It intentionally does NOT decide whether a signal
is "reliable" — that is a downstream, threshold-based judgment (research/exclusion_rules.md) made
by the caller using the report-count fields this module also returns.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

Z_95 = 1.959963984540054  # scipy.stats.norm.ppf(0.975), hardcoded to avoid a scipy import here


@dataclass(frozen=True)
class RorResult:
    a: float
    b: float
    c: float
    d: float
    continuity_correction_applied: bool
    ror: float
    log_ror: float
    se_log_ror: float
    ci_low: float
    ci_high: float


def compute_ror(a: int, b: int, c: int, d: int, *, continuity_correction: float = 0.5) -> RorResult:
    """Compute the Reporting Odds Ratio and its 95% CI for one drug x adverse-event 2x2 table.

    Parameters
    ----------
    a : reports of drug D with event E
    b : reports of drug D with other events
    c : reports of other drugs with event E
    d : reports of other drugs with other events
    continuity_correction : value added to all four cells when any cell is zero (Haldane-Anscombe
        correction, research/analysis_plan.md Sec. 1). Must be positive whenever any cell is zero --
        logROR and its standard error are mathematically undefined (log(0) / division by zero) for a
        zero-cell table with no correction, and this function raises rather than returning a
        plausible-looking value for an undefined quantity.

    Raises
    ------
    ValueError if any input count is negative, or if a cell is zero and continuity_correction <= 0.
    """
    if any(x < 0 for x in (a, b, c, d)):
        raise ValueError(f"Contingency table counts must be non-negative, got a={a}, b={b}, c={c}, d={d}")

    has_zero_cell = 0 in (a, b, c, d)
    correction_applied = False
    a_, b_, c_, d_ = float(a), float(b), float(c), float(d)
    if has_zero_cell:
        if continuity_correction <= 0:
            raise ValueError(
                f"Cell is zero (a={a}, b={b}, c={c}, d={d}) and continuity_correction={continuity_correction} "
                "is not positive -- logROR/SE are undefined without a continuity correction. Pass a positive "
                "continuity_correction (default 0.5, Haldane-Anscombe) instead of disabling it."
            )
        a_, b_, c_, d_ = a_ + continuity_correction, b_ + continuity_correction, c_ + continuity_correction, d_ + continuity_correction
        correction_applied = True

    ror = (a_ * d_) / (b_ * c_)
    log_ror = math.log(ror)
    se_log_ror = math.sqrt(1 / a_ + 1 / b_ + 1 / c_ + 1 / d_)
    ci_low = math.exp(log_ror - Z_95 * se_log_ror)
    ci_high = math.exp(log_ror + Z_95 * se_log_ror)

    return RorResult(
        a=a, b=b, c=c, d=d,
        continuity_correction_applied=correction_applied,
        ror=ror,
        log_ror=log_ror,
        se_log_ror=se_log_ror,
        ci_low=ci_low,
        ci_high=ci_high,
    )


@dataclass(frozen=True)
class PrrResult:
    """Proportional Reporting Ratio -- optional secondary measure (Sec. 11), not primary."""

    prr: float
    chi_square: float


def compute_prr(a: int, b: int, c: int, d: int, *, continuity_correction: float = 0.5) -> PrrResult:
    if any(x < 0 for x in (a, b, c, d)):
        raise ValueError(f"Contingency table counts must be non-negative, got a={a}, b={b}, c={c}, d={d}")

    a_, b_, c_, d_ = float(a), float(b), float(c), float(d)
    if 0 in (a, b, c, d):
        if continuity_correction <= 0:
            raise ValueError(
                f"Cell is zero (a={a}, b={b}, c={c}, d={d}) and continuity_correction={continuity_correction} "
                "is not positive -- PRR reporting rates are undefined without a continuity correction."
            )
        a_, b_, c_, d_ = a_ + continuity_correction, b_ + continuity_correction, c_ + continuity_correction, d_ + continuity_correction

    reporting_rate_d = a_ / (a_ + b_)
    reporting_rate_other = c_ / (c_ + d_)
    prr = reporting_rate_d / reporting_rate_other

    n = a_ + b_ + c_ + d_
    expected_a = (a_ + b_) * (a_ + c_) / n
    chi_square = (a_ - expected_a) ** 2 / expected_a if expected_a > 0 else float("nan")

    return PrrResult(prr=prr, chi_square=chi_square)


def p_activity_from_nm(value_nm: float) -> float:
    """Standardized pActivity = 9 - log10(value_nM), per project brief Sec. 2.

    Only meaningful for relation == '=' measurements (exact potency values), never for
    censored (>/<) measurements -- caller is responsible for that check.
    """
    if value_nm <= 0:
        raise ValueError(f"value_nm must be positive, got {value_nm}")
    return 9.0 - math.log10(value_nm)
