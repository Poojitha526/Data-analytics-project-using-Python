# Supermarket Sales Analysis (Python)

## Files
- `analysis.py`: data cleaning, sales calculation/reconciliation, summary tables, charts, and reported-result verification.
- `requirements.txt`: Python packages.
- `supermarket_sales.csv`: add your actual dataset here (not included because the Google Sheet could not be fetched directly).
- `outputs/`: generated after running the script.

## 1. Download the actual Google Sheet as CSV
Open your spreadsheet in Google Sheets:
1. Click **File → Download → Comma Separated Values (.csv)**.
2. Save the downloaded file in this folder as **`supermarket_sales.csv`**.
3. If your sheet has multiple tabs, first select the correct tab (the one with the 500 sales transactions), then download it.

## 2. Install and run
Open a terminal in this folder and run:

```bash
python -m pip install -r requirements.txt
python analysis.py
```

If `python` is not recognised, try `py` instead:

```bash
py -m pip install -r requirements.txt
py analysis.py
```

## 3. Outputs
The script creates:
- `analysis_summary.txt`
- `data_quality.csv`
- product, branch, city, category, customer-type and payment summaries (when matching columns exist)
- `reported_results_verification.csv` — compares the actual CSV calculations with the values in your brief
- charts as PNG files
- `sales_reconciliation.csv` if both Sales and Quantity × Unit Price are available

## Important
The values in the brief are treated as claims to verify, not as guaranteed results. Column names may vary; the script recognises common alternatives. Review `sales_reconciliation.csv` if the given Sales column differs from Quantity × Unit Price.
