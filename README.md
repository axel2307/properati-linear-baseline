# Properati linear baseline

A small Streamlit portfolio project that rebuilds an early handwritten linear regression as an auditable baseline for **price targets in an author-provided dataset, expressed in USD/m²**. The interface uses Rioplatense Spanish; implementation and documentation are in English.

The default application uses a minimized projection of **the author's own supplied `properati.csv`**. It does not substitute a generated dataset. The author states that the supplied dataset is fictional and explicitly authorized publication of this projection. **That declaration has not been independently verified.** The dataset and its evaluation results do not represent market prices or establish real estate accuracy. This is an educational model, not a current valuation, a transaction price estimator, or professional appraisal advice.

`data/demo.csv` retains eight fields: `property_type`, `neighborhood`, `area_total`, `area_covered`, `rooms`, `lat`, `lon`, and `price_usd`. Coordinates are rounded to three decimal places before the projection is validated and deduplicated again. Rounding reduces coordinate precision but is not a guarantee of anonymity. Addresses, contacts, descriptions, listing URLs and other free text are excluded. The original file is not included. No independent source provenance or third-party dataset license is claimed; publication of this projection relies on the author's explicit authorization and declaration. See `PRIVACY.md` for the data-handling details.

## Run locally

Use Python 3.12. From this project directory:

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell instead: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

The default application does not offer file uploads. To enable uploads in your own installation, set the environment variable **before** starting Streamlit:

```powershell
# Windows PowerShell
$env:PROPERATI_ALLOW_UPLOADS = "1"
streamlit run app.py
```

```bash
# macOS / Linux
PROPERATI_ALLOW_UPLOADS=1 streamlit run app.py
```

Uploaded files travel from the browser to the server running the application. A visible acknowledgement is required before the uploader appears. Prefer running locally for private files. The app does not write uploads to disk, use `st.cache_data` for them, show raw records, or display individual coordinates. Files and derived frames necessarily exist in server memory during processing. Infrastructure outside this app may have its own logging or retention policies.

Do not upload a file until you have checked its license and privacy. The author's fictional-data declaration applies only to the bundled projection, not to arbitrary uploads. A filename or source brand does not establish provenance or redistribution rights.

## What the model does

The target is `usd_m2`, calculated from the dataset's recorded `price_usd` divided by total area. Features are the number of rooms, total area, covered-to-total-area ratio, property type and neighborhood. The form computes the ratio directly from the two entered areas; bathrooms and amenities are deliberately absent because the supported dataset does not provide them.

The fit uses `numpy.linalg.lstsq`, one intercept, training-only numeric means and scales, and one omitted reference category for each categorical feature. It does not invert `X.T @ X`. Every prediction is built by feature name in the order learned on the training frame, so input column order cannot change its meaning. The UI displays design-matrix rank and condition number; a rank-deficient fit is reported rather than hidden.

The model rejects invalid areas, fractional or nonpositive room counts, ratios outside `(0, 1]`, unseen categories, unseen type/neighborhood combinations, and numeric values outside their individual training ranges. If covered area is supplied, it must be positive, no larger than total area, and agree with the ratio. Nonpositive or nonfinite predictions are also rejected; nothing is silently clipped or extrapolated. These checks are deliberately conservative but do **not** establish joint statistical support for every combination of numeric values.

The model also rejects feature magnitudes and target values above `1e100` before numerical reductions. This is an arithmetic safety limit, not a market-price cutoff. Both the unit estimate and its implied total must be finite and positive.

For a supported query, the interface also shows the predicted USD/m² multiplied by the entered total area. This is an implied total under the fitted dataset model, not a separate independent prediction or a market price. No confidence or prediction interval is claimed from training residuals.

## Data contract

`data.py` exposes `load_demo`, `load_csv`, `prepare_frame`, `split_data`, and `synthetic_data`. The application calls `load_demo()` to validate the bundled eight-column `data/demo.csv`; a missing or invalid projection stops the app without falling back to generated data. `synthetic_data` is retained only for automated test fixtures.

For optional private uploads, UTF-8 CSV and tab-separated files are accepted through a validated parser, up to 200 MiB and 200,000 rows. An uploaded file needs these **exact raw column names**:

```text
operation, property_type, place_name, state_name, lat, lon, price,
currency, surface_total_in_m2, surface_covered_in_m2, rooms
```

Only records marked `operation=sell`, `state_name=Capital Federal`, `currency=USD`, and with supported types (`apartment`, `house`, `PH`) and allowlisted neighborhood names survive. These are checks of source values, not verification of real-world facts. Positive finite price targets and surfaces, covered area no greater than total, positive integer room counts and coordinates within a CABA plausibility rectangle are required. This excludes other locations, converted-currency values, incomplete records and unknown neighborhood labels. Complete-case filtering can discard most source rows and creates selection bias; accepted data should not be treated as representative of the entire original file. Additional columns such as descriptions and listing URLs are discarded, but they still reach the server if present in an upload.

The resulting canonical model frame contains:

| Column | Meaning |
| --- | --- |
| `property_type` | Property category |
| `neighborhood` | Neighborhood category |
| `area_total`, `area_covered` | Positive areas in m²; covered area must not exceed total |
| `rooms` | Positive whole number of rooms |
| `lat`, `lon` | Valid latitude and longitude, used for grouping only |
| `price_usd` | Positive price target recorded in the dataset, expressed in USD |
| `usd_m2` | Price divided by total area |
| `ratio` | Covered area divided by total area |
| `spatial_group` | Coarse geographic cell used to separate train and evaluation |

See `data.py` for validation and its neighborhood allowlist. Loader reports include aggregate accepted/rejected/duplicate counts; the interface keeps the training/evaluation counts and never displays uploaded rows. Optional sensitive columns are not part of the model contract. Raw column aliases are not inferred.

## Evaluation and leakage controls

1. Validate the data and remove duplicate location/feature records without using their target values as the duplicate key.
2. Reserve complete spatial groups with a fixed seed (`42`) and approximately 20% held-out data. The actual fraction depends on group sizes.
3. Learn categories, numeric scaling, ranges and coefficients using only the training partition.
4. Evaluate supported held-out rows against their observed USD/m². Report mean absolute error, median absolute error, and coverage.
5. Compare against the **training target median on exactly the same supported held-out rows**. Unsupported rows and their rejection counts are reported separately. An empty supported subset produces no fabricated metric.

The interactive predictor keeps that same training-only model; it does not refit with the held-out target values. Metrics therefore describe the displayed fitted model and split. For the bundled projection, they describe only the author-declared fictional dataset, not market performance. Coverage matters: errors on the supported subset cannot be presented as errors over all records, nor directly compared with another app's errors when that app supports different rows.

Spatial groups reduce location leakage but are not distance-buffered spatial blocks. Locations on opposite cell boundaries can remain close. Coordinate rounding changes some group assignments and duplicate fingerprints. Feature-based deduplication cannot prove that every repeated record was found and may collapse distinct records with identical observed features. No reliable observation date is assumed, so this evaluation is **not** a temporal forecast. A temporal split would require dates whose meaning has been established.

## Limitations and methodology review

This prototype preserves a simple linear baseline. It does not add a geocoding service, external data provider, model selection search, or a more complex valuation platform. Numeric extrapolation controls, scaling and least-squares solving are correctness improvements; any larger methodological change should be reviewed against the actual source data and evaluation results first.

The author's declaration of fiction is reported transparently, not treated as independently established provenance. This model does not infer whether arbitrary uploaded values correspond to real-world asking prices, transactions or simulations. Linear assumptions omit property condition, building age, floor, orientation and many other factors. Category coefficients reflect associations in the training sample, not causal effects. Sparse categories and correlated features can make fits unstable. No interval has been calibrated on independent data.

This repository makes no market-accuracy claim or independent source-license assertion. Metrics are computed from the shipped projection rather than copied from results on the original file; coordinate minimization and subsequent validation can change the retained rows and evaluation split.

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The model tests cover shuffled input columns, a single intercept and reference categories, a rank-deficient design, unseen categories and combinations, invalid inputs, range checks, nonpositive predictions, same-subset baseline evaluation, empty coverage, and independence from held-out targets. Shared ingestion and split tests cover parser and data-preparation behavior. Streamlit tests exercise the bundled author projection, the prediction form, invalid surfaces, upload acknowledgement, and failure without a generated-data fallback when the projection is unavailable. CI runs the tests on Python 3.12.

## Project structure

```text
app.py                 Streamlit interface (Rioplatense Spanish)
model.py               Named, scaled OLS fit and support-aware evaluation
data.py                Validated demo/upload loading and spatial split
data/demo.csv          Authorized eight-field projection of the author's file
tests/                 Model and data invariants
requirements.txt       Pinned runtime dependencies
requirements-dev.txt   Test dependencies
.github/workflows/     Continuous integration
```
