from pathlib import Path
import re
import sys
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "supermarket_sales.csv"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

# Findings supplied in the project brief; script checks these against the CSV.
EXPECTED = {
    "top_product": ("Cheese", 27906.30),
    "top_branch": ("C", 72469.45),
    "top_category": ("Beverages", 56108.24),
    "payment_method": ("UPI", 127),
    "member_average": 483.14,
    "normal_average": 497.07,
    "average_rating": 3.99,
}

ALIASES = {
    "product": ["product", "product name", "item", "item name"],
    "branch": ["branch", "store branch", "store"],
    "city": ["city", "location"],
    "category": ["category", "product category", "product line", "department"],
    "customer_type": ["customer type", "membership", "customer segment"],
    "quantity": ["quantity", "qty", "units sold"],
    "unit_price": ["unit price", "price per unit", "price"],
    "payment_method": ["payment method", "payment", "payment type"],
    "rating": ["rating", "customer rating"],
    "sales": ["sales", "total sales", "revenue", "total"],
}

def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()

def find_col(df, key):
    cols = {norm(c): c for c in df.columns}
    for alias in ALIASES[key]:
        if norm(alias) in cols:
            return cols[norm(alias)]
    for alias in ALIASES[key]:
        for n, original in cols.items():
            if norm(alias) in n:
                return original
    return None

def save_bar(series, title, xlabel, ylabel, filename, horizontal=False):
    if series is None or series.empty:
        return
    plt.figure(figsize=(10, 6))
    if horizontal:
        series.sort_values().plot(kind="barh")
    else:
        series.plot(kind="bar")
        plt.xticks(rotation=35, ha="right")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(OUT / filename, dpi=160)
    plt.close()

def main():
    if not DATA_FILE.exists():
        print(f"\nDataset not found: {DATA_FILE}")
        print("Download the Google Sheet as CSV, save it as supermarket_sales.csv here,")
        print("then run this script again. The findings cannot be verified without the CSV.")
        sys.exit(1)

    df = pd.read_csv(DATA_FILE)
    if df.empty:
        raise ValueError("The CSV has no data rows.")
    original_rows = len(df)
    columns = {k: find_col(df, k) for k in ALIASES}

    if columns["product"] is None:
        raise ValueError(f"Product column not found. Columns in file: {list(df.columns)}")

    # Basic data quality checks
    quality = pd.DataFrame({
        "Metric": ["Rows loaded", "Columns", "Duplicate rows", "Rows with at least one missing value"],
        "Value": [original_rows, len(df), int(df.duplicated().sum()), int(df.isna().any(axis=1).sum())]
    })
    quality.to_csv(OUT / "data_quality.csv", index=False)

    for key in ["quantity", "unit_price", "sales", "rating"]:
        if columns[key]:
            df[columns[key]] = pd.to_numeric(df[columns[key]], errors="coerce")

    # Sales calculation and reconciliation
    if columns["quantity"] and columns["unit_price"]:
        df["Calculated Sales"] = df[columns["quantity"]] * df[columns["unit_price"]]
        if columns["sales"]:
            df["Sales Difference"] = df[columns["sales"]] - df["Calculated Sales"]
            valid_diff = df["Sales Difference"].dropna()
            if valid_diff.empty or valid_diff.abs().max() <= 0.02:
                df["Analysis Sales"] = df["Calculated Sales"]
                sales_note = "Used Quantity × Unit Price; supplied Sales agrees within ₹0.02."
            else:
                df["Analysis Sales"] = df[columns["sales"]]
                sales_note = "Used supplied Sales because it differs from Quantity × Unit Price. See sales_reconciliation.csv."
            df[["Calculated Sales", "Sales Difference"]].to_csv(OUT / "sales_reconciliation.csv", index=False)
        else:
            df["Analysis Sales"] = df["Calculated Sales"]
            sales_note = "Calculated Sales = Quantity × Unit Price."
    elif columns["sales"]:
        df["Analysis Sales"] = df[columns["sales"]]
        sales_note = "Used the existing Sales column; quantity and/or unit price was unavailable."
    else:
        raise ValueError("A Sales column or both Quantity and Unit Price columns are required.")

    data = df[df["Analysis Sales"].notna()].copy()
    if data.empty:
        raise ValueError("No valid sales values were found.")

    # Summary tables
    summaries = {}
    for key in ["product", "branch", "city", "category", "customer_type", "payment_method"]:
        col = columns[key]
        if col:
            summary = data.groupby(col, dropna=False)["Analysis Sales"].agg(
                Transactions="count", Total_Sales="sum", Average_Sale="mean"
            ).sort_values("Total_Sales", ascending=False)
            summaries[key] = summary
            summary.to_csv(OUT / f"{key}_sales_summary.csv")

    if columns["payment_method"]:
        data[columns["payment_method"]].value_counts(dropna=False).rename("Transactions").to_csv(
            OUT / "payment_method_counts.csv"
        )

    # Visualisations
    if "product" in summaries:
        save_bar(summaries["product"]["Total_Sales"].head(10), "Top 10 Products by Sales",
                 "Product", "Sales (₹)", "top_products_sales.png")
    if "branch" in summaries:
        save_bar(summaries["branch"]["Total_Sales"], "Total Sales by Branch",
                 "Branch", "Sales (₹)", "branch_sales.png")
    if "category" in summaries:
        save_bar(summaries["category"]["Total_Sales"], "Total Sales by Category",
                 "Category", "Sales (₹)", "category_sales.png")
    if columns["payment_method"]:
        counts = data[columns["payment_method"]].value_counts(dropna=False)
        save_bar(counts, "Transactions by Payment Method", "Payment Method",
                 "Number of Transactions", "payment_methods.png")
    if columns["rating"]:
        ratings = data[columns["rating"]].dropna()
        if not ratings.empty:
            plt.figure(figsize=(8, 5))
            ratings.plot(kind="hist", bins=10, edgecolor="black")
            plt.title("Distribution of Customer Ratings")
            plt.xlabel("Customer Rating")
            plt.ylabel("Number of Transactions")
            plt.tight_layout()
            plt.savefig(OUT / "customer_ratings.png", dpi=160)
            plt.close()
    if columns["customer_type"]:
        avg = data.groupby(columns["customer_type"])["Analysis Sales"].mean().sort_values()
        save_bar(avg, "Average Transaction Value by Customer Type", "Customer Type",
                 "Average Sale (₹)", "customer_type_average.png")

    # Results and comparison against the project brief
    checks = []
    def check(metric, expected, actual, numeric=False, tolerance=0.02):
        if actual is None or pd.isna(actual):
            checks.append({"Metric": metric, "Reported": expected, "Actual": "Unavailable", "Status": "NOT CHECKED"})
            return
        if numeric:
            ok = abs(float(actual) - float(expected)) <= tolerance
        else:
            ok = str(actual).strip().lower() == str(expected).strip().lower()
        checks.append({"Metric": metric, "Reported": expected, "Actual": actual, "Status": "MATCH" if ok else "DIFFERENCE"})

    if "product" in summaries:
        s = summaries["product"]["Total_Sales"]
        p = s.idxmax()
        check("Top product", EXPECTED["top_product"][0], p)
        check("Top product sales (₹)", EXPECTED["top_product"][1], s.loc[p], True)
    else:
        check("Top product", "Cheese", None)
    if "branch" in summaries:
        s = summaries["branch"]["Total_Sales"]
        p = s.idxmax()
        check("Top branch", EXPECTED["top_branch"][0], p)
        check("Top branch sales (₹)", EXPECTED["top_branch"][1], s.loc[p], True)
    else:
        check("Top branch", "C", None)
    if "category" in summaries:
        s = summaries["category"]["Total_Sales"]
        p = s.idxmax()
        check("Top category", EXPECTED["top_category"][0], p)
        check("Top category sales (₹)", EXPECTED["top_category"][1], s.loc[p], True)
    else:
        check("Top category", "Beverages", None)
    if columns["payment_method"]:
        counts = data[columns["payment_method"]].value_counts()
        p = counts.idxmax()
        check("Most-used payment method", EXPECTED["payment_method"][0], p)
        check("UPI transaction count", EXPECTED["payment_method"][1], counts.get("UPI", 0), True, 0)
    else:
        check("Most-used payment method", "UPI", None)
    if columns["customer_type"]:
        avgs = data.groupby(data[columns["customer_type"]].astype(str))["Analysis Sales"].mean()
        member = next((v for k, v in avgs.items() if k.lower() == "member"), None)
        normal = next((v for k, v in avgs.items() if k.lower() == "normal"), None)
        check("Member average transaction (₹)", EXPECTED["member_average"], member, True)
        check("Normal average transaction (₹)", EXPECTED["normal_average"], normal, True)
    else:
        check("Customer-type averages", "Member and Normal averages", None)
    if columns["rating"]:
        check("Average customer rating", EXPECTED["average_rating"], data[columns["rating"]].mean(), True)
    else:
        check("Average customer rating", EXPECTED["average_rating"], None)

    pd.DataFrame(checks).to_csv(OUT / "reported_results_verification.csv", index=False)
    with open(OUT / "analysis_summary.txt", "w", encoding="utf-8") as f:
        f.write("SUPERMARKET SALES ANALYSIS\n")
        f.write("=" * 28 + "\n")
        f.write(f"Rows loaded: {original_rows}\n")
        f.write(f"Rows used for sales analysis: {len(data)}\n")
        f.write(f"Total sales: ₹{data['Analysis Sales'].sum():,.2f}\n")
        f.write(f"Average transaction sales: ₹{data['Analysis Sales'].mean():,.2f}\n")
        f.write(f"Sales calculation note: {sales_note}\n\n")
        f.write("Top findings from the actual CSV:\n")
        for key, label in [("product", "Product"), ("branch", "Branch"), ("category", "Category")]:
            if key in summaries:
                s = summaries[key]["Total_Sales"]
                f.write(f"- Highest {label.lower()} sales: {s.idxmax()} — ₹{s.max():,.2f}\n")
        if columns["payment_method"]:
            c = data[columns["payment_method"]].value_counts()
            f.write(f"- Most-used payment method: {c.idxmax()} — {int(c.max())} transactions\n")
        if columns["customer_type"]:
            avgs = data.groupby(columns["customer_type"])["Analysis Sales"].mean()
            f.write("- Average sale by customer type:\n")
            for k, v in avgs.items():
                f.write(f"  - {k}: ₹{v:,.2f}\n")
        if columns["rating"]:
            f.write(f"- Average rating: {data[columns['rating']].mean():.2f}/5\n")
        f.write("\nSee reported_results_verification.csv to compare with the values in the project brief.\n")

    print("Analysis complete.")
    print(f"Outputs saved in: {OUT}")
    print(f"Sales calculation note: {sales_note}")
    print("Open outputs/reported_results_verification.csv to see which reported findings match the actual data.")

if __name__ == "__main__":
    main()
