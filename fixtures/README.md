# Synthetic fixtures

Original deterministic curves; no instrument or biological data. MIT licensed. Run `uv run python fixtures/generate.py` to regenerate. UTF-8, LF, 17 significant digits.

The two demonstration traces have 601 points across 0–10 min. Both contain exp(-0.5*((t-4.5)/0.45)^2). The clean trace adds a 0.12-amplitude feature at 7 min (width 0.2); the neighboring trace adds a 0.30-amplitude feature at 5.35 min (width 0.25).

Triangle: total 2; [0.5,1.5] area 1.5, fraction 75%. Irregular: total 6; [0.5,3.5] area 5.5. The invalid file must reject duplicate time on line 4.

| File | SHA-256 |
|---|---|
| `clean-trace.csv` | `6d07f7bebdb3c04b711f643975648c478f96bf0dd57aa3291f6762218aa62d6f` |
| `invalid-duplicate-time.csv` | `4401e8b888c7a275f0c35163b80f99fdedcc3907fbe695aa661ccacb918feb1a` |
| `irregular.csv` | `93c494e620f8371cf8007c48568809f5ba8b2a55e6e8b39408b6eba822aec9da` |
| `neighboring-feature.csv` | `fb73c5693953bbff2829f77df8c899b04a70f85e0c6c9f567a1a486e13d8a142` |
| `triangle.csv` | `522d11d99a01cf4397e546de142c517cccca70b348acfb7adfa5649bb35869b0` |
