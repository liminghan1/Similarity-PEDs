"""Unit conversion to standardized nanomolar (nM), for the units ChEMBL actually reports on
Ki/IC50/EC50/Kd measurements. Unrecognized units are NOT guessed at -- the caller gets None and
must store the raw value without a standardized_value_nm, per the project's no-fabrication rule.
"""

_TO_NANOMOLAR: dict[str, float] = {
    "nM": 1.0,
    "uM": 1_000.0,
    "10'-6M": 1_000.0,
    "mM": 1_000_000.0,
    "10'-3M": 1_000_000.0,
    "M": 1_000_000_000.0,
    "pM": 0.001,
    "10'-12M": 0.001,
    "fM": 0.000_001,
}


def to_nanomolar(value: float, units: str) -> float | None:
    factor = _TO_NANOMOLAR.get(units)
    if factor is None:
        return None
    return value * factor
