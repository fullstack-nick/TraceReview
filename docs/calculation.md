# Calculation contract

`csv-time-signal-v1` interprets an uploaded UTF-8 CSV with optional BOM, LF/CRLF line endings, and exactly `time_min,signal_au` in that order. Standard CSV quoting is accepted; multiline fields and blank records are rejected. The final newline is optional. Only surrounding ASCII spaces/tabs in numeric cells are ignored. Original bytes are retained unchanged.

Numeric grammar: `[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?`. Each decoded cell is at most 128 characters. Finite binary64 values are required; decimal nonzero values that underflow to zero are rejected. Times must remain strictly increasing after binary64 conversion. Negative signals are rejected; negative times and signed zero are permitted. There must be 2–2,000 points, a maximum 262,144 file bytes, and a finite positive entire-trace area. Requests are limited to 524,288 bytes including multipart overhead.

Input failures identify the physical line/column when applicable. There is no automatic sorting, deduplication, missing-value replacement, smoothing, baseline correction, or peak detection. Nonnegative input is this application’s contract, not a claim about the validity of negative experimental measurements.

## Integration

`linear-trapezoid-v1` treats adjacent measured points as straight segments. For interval endpoints `a < b` inside the measured range, interpolate a signal at each endpoint and combine them with measured points strictly between the endpoints. Integrate these points using `numpy.trapezoid(y, x=t)`.

`segment area = (t[i+1] − t[i]) × (y[i] + y[i+1]) / 2`

| Output | Definition | Unit |
|---|---|---|
| Total area | Integration over first through last measured time | AU·min |
| Selected area | Integration between the selected endpoints | AU·min |
| Selected-region area fraction | `100 × selected area / total area` | % |

Full-trace bounds return the same area object value and exactly 100%. A selected zero-signal region returns zero and 0%. Intermediate overflow or nonfinite results reject with `numeric_range`; no out-of-range input is silently clipped. Tiny positive numerical overshoot above the total, at most `total × 1e-12`, is clamped to total; larger overshoot rejects. No rounded display value is used in another calculation.

## Independent examples

| Points | Interval | Total | Selected | Fraction |
|---|---|---:|---:|---:|
| `(0,0), (1,2), (2,0)` | 0.5–1.5 | 2 | 1.5 | 75% |
| Same triangle | 0–2 | 2 | 2 | 100% |
| Same triangle, both bounds in one segment | 0.25–0.75 | 2 | 0.5 | 25% |
| `(0,1), (2,3)` | 0.5–1.5 | 4 | 2 | 50% |
| `(0,0), (1,2), (3,2), (4,0)` | 0.5–3.5 | 6 | 5.5 | 91⅔% |
| `(0,0), (1,0), (2,2)` | 0–0.5 | 1 | 0 | 0% |

The authoritative pure Python module has no HTTP, ORM, or UI dependency. Preview and save use the same function. Save ignores no client result: result/author/time fields are unsupported inputs and rejected. Saved binary64 numbers are preserved as database floats and JSON numbers; export never recalculates. Server timestamps are UTC; the UI formats dates with a timezone label.

## Display and scope

Workspace areas use six significant digits; percentage uses two decimal places. Small nonzero/near-100 values use inequality labels rather than misleading rounded endpoints. Inputs, Data, and report details retain full round-trip numeric precision. The plot uses straight SVG line segments with simplification disabled.

The denominator is always the entire uploaded trace, including any neighboring feature. Changing selected bounds does not change the denominator. The examples are original deterministic synthetic functions with 601 samples; their formulas and SHA-256 hashes are in [fixtures/README.md](../fixtures/README.md).

This calculation has no biological, purity, sample-release, or instrument-specific interpretation. No human scientific validation is claimed. Measurements with a baseline that needs correction must be prepared outside this application, and that preprocessing is outside the preserved source history.
