import math

import pytest

from backend.app.analytics.signals import compute_prr, compute_ror, p_activity_from_nm


class TestComputeRor:
    def test_balanced_table_gives_ror_of_one(self):
        result = compute_ror(10, 10, 10, 10)
        assert result.ror == pytest.approx(1.0)
        assert result.log_ror == pytest.approx(0.0, abs=1e-9)
        assert not result.continuity_correction_applied

    def test_ci_contains_point_estimate(self):
        result = compute_ror(25, 175, 40, 960)
        assert result.ci_low < result.ror < result.ci_high

    def test_manual_calculation_matches_formula(self):
        a, b, c, d = 25, 175, 40, 960
        expected_ror = (a * d) / (b * c)
        expected_log_ror = math.log(expected_ror)
        expected_se = math.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
        result = compute_ror(a, b, c, d)
        assert result.ror == pytest.approx(expected_ror)
        assert result.log_ror == pytest.approx(expected_log_ror)
        assert result.se_log_ror == pytest.approx(expected_se)
        assert result.ci_low == pytest.approx(math.exp(expected_log_ror - 1.959963984540054 * expected_se))
        assert result.ci_high == pytest.approx(math.exp(expected_log_ror + 1.959963984540054 * expected_se))

    def test_zero_cell_triggers_continuity_correction(self):
        result = compute_ror(0, 100, 5, 900)
        assert result.continuity_correction_applied
        # with correction, a=0.5 rather than 0 -> finite, positive ROR
        assert math.isfinite(result.ror)
        assert result.ror > 0

    def test_zero_cell_without_correction_raises(self):
        # continuity_correction=0 disables the correction explicitly; logROR/SE are
        # mathematically undefined for a zero cell in that case, so this must raise
        # rather than silently returning a plausible-looking number (e.g. ROR=0).
        with pytest.raises(ValueError):
            compute_ror(0, 100, 5, 900, continuity_correction=0)

    def test_negative_counts_rejected(self):
        with pytest.raises(ValueError):
            compute_ror(-1, 10, 10, 10)

    def test_higher_reporting_rate_in_drug_gives_ror_above_one(self):
        # Drug D: 50/150 reports are event E. Other drugs: 10/500 reports are event E.
        result = compute_ror(50, 100, 10, 490)
        assert result.ror > 1
        assert result.ci_low > 1  # signal does not cross the null


class TestComputePrr:
    def test_balanced_table_gives_prr_of_one(self):
        result = compute_prr(10, 10, 10, 10)
        assert result.prr == pytest.approx(1.0)


class TestPActivity:
    def test_one_nanomolar_gives_pactivity_nine(self):
        assert p_activity_from_nm(1.0) == pytest.approx(9.0)

    def test_one_micromolar_gives_pactivity_six(self):
        assert p_activity_from_nm(1000.0) == pytest.approx(6.0)

    def test_nonpositive_value_rejected(self):
        with pytest.raises(ValueError):
            p_activity_from_nm(0.0)
        with pytest.raises(ValueError):
            p_activity_from_nm(-5.0)
