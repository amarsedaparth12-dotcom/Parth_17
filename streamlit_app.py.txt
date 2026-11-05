
import re
from io import BytesIO
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Mutual Fund Analytics",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Mutual Fund Data Analytics Tool")
st.write("Upload raw mutual fund data to clean, format and analyse it.")

ALIASES = {
    "Fund Name": ["fund name", "scheme name", "scheme"],
    "Date": ["date", "as of date", "valuation date"],
    "NAV": ["nav", "nav price", "current nav", "price"],
    "AUM": ["aum", "assets under management"],
    "Inflow": ["inflow", "inflows", "subscriptions"],
    "Outflow": ["outflow", "outflows", "redemptions"],
    "Net Flow": ["net flow", "net flows"],
    "Fund Category": ["fund category", "category", "asset class"],
    "Country": ["country", "country/region", "region"],
    "Sector": ["sector", "sector focus", "industry"],
    "Daily Return": ["daily return", "daily return (%)", "return %"],
    "Expense Ratio": ["expense ratio", "ter"],
    "Units": ["units", "quantity"],
    "Invested Value": ["invested", "invested (₹)", "cost value"],
    "Current Value": ["current value", "current value (₹)", "market value"],
    "Gain/Loss": ["gain/loss", "profit/loss", "p&l"],
    "Allocation": ["allocation", "allocation %", "portfolio weight"]
}

def normalise(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()

def standardise(df):
    df = df.copy()
    existing = {normalise(c): c for c in df.columns}
    rename = {}

    for standard, aliases in ALIASES.items():
        for name in [standard] + aliases:
            key = normalise(name)
            if key in existing:
                rename[existing[key]] = standard
                break

    return df.rename(columns=rename)

def create_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Cleaned Data", index=False)
        df.describe(include="all").transpose().to_excel(
            writer, sheet_name="Summary"
        )
    return output.getvalue()

uploaded = st.file_uploader(
    "Upload Mutual Fund Raw Data",
    type=["xlsx", "xls", "csv"]
)

if uploaded is None:
    st.info("Upload your Excel or CSV file to begin.")
    st.write("""
    ### Tool Features
    - Raw Data Upload
    - Automatic Column Standardisation
    - Blank Rows and Duplicate Removal
    - NAV and AUM Analysis
    - Fund Flow Analysis
    - Sector-wise and Country-wise Charts
    - Excel and CSV Download
    """)
    st.stop()

try:
    if uploaded.name.lower().endswith(".csv"):
        raw = pd.read_csv(uploaded)
    else:
        raw = pd.read_excel(uploaded)
except Exception as error:
    st.error(f"File reading error: {error}")
    st.stop()

st.header("1. Original Raw Data")
st.write(f"Rows: {len(raw)} | Columns: {len(raw.columns)}")
st.dataframe(raw.head(30), use_container_width=True)

data = standardise(raw)
data = data.dropna(how="all").drop_duplicates().copy()

numeric_columns = [
    "NAV", "AUM", "Inflow", "Outflow", "Net Flow",
    "Daily Return", "Expense Ratio", "Units",
    "Invested Value", "Current Value", "Gain/Loss",
    "Allocation"
]

for col in numeric_columns:
    if col in data.columns:
        values = data[col].astype(str)
        values = values.str.replace(",", "", regex=False)
        values = values.str.replace("₹", "", regex=False)
        values = values.str.replace("$", "", regex=False)
        values = values.str.replace("%", "", regex=False)
        data[col] = pd.to_numeric(values, errors="coerce")

if "Date" in data.columns:
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")

if "Net Flow" not in data.columns:
    if "Inflow" in data.columns and "Outflow" in data.columns:
        data["Net Flow"] = (
            data["Inflow"].fillna(0) -
            data["Outflow"].fillna(0)
        )

if "Gain/Loss" not in data.columns:
    if "Current Value" in data.columns and "Invested Value" in data.columns:
        data["Gain/Loss"] = (
            data["Current Value"] - data["Invested Value"]
        )

if "Allocation" not in data.columns and "Current Value" in data.columns:
    total = data["Current Value"].sum()
    if total != 0:
        data["Allocation"] = data["Current Value"] / total * 100

st.header("2. Cleaned and Formatted Data")

c1, c2, c3 = st.columns(3)
c1.metric("Original Rows", len(raw))
c2.metric("Clean Rows", len(data))
c3.metric("Duplicates Removed", len(raw) - len(data))

st.dataframe(data, use_container_width=True)

st.download_button(
    "Download Cleaned CSV",
    data.to_csv(index=False).encode("utf-8-sig"),
    file_name="cleaned_mutual_fund_data.csv",
    mime="text/csv"
)

st.download_button(
    "Download Cleaned Excel",
    create_excel(data),
    file_name="mutual_fund_analysis.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.header("3. Mutual Fund Analysis")

numeric = data.select_dtypes(include="number").columns.tolist()

if numeric:
    metric = st.selectbox("Select Analysis Metric", numeric)

    st.metric(
        f"Total {metric}",
        f"{data[metric].sum():,.2f}"
    )

    group_columns = [
        c for c in [
            "Fund Name", "Fund Category",
            "Country", "Sector"
        ] if c in data.columns
    ]

    if group_columns:
        group = st.selectbox("Group Analysis By", group_columns)

        chart_data = (
            data.groupby(group)[metric]
            .sum()
            .sort_values(ascending=False)
            .head(20)
        )

        st.subheader(f"{metric} by {group}")
        st.bar_chart(chart_data)

    st.subheader("Statistical Summary")
    st.dataframe(data[numeric].describe().T)

else:
    st.warning("No numeric columns found in uploaded data.")

if "Date" in data.columns and numeric:
    st.header("4. Date-wise Trend Analysis")

    trend_metric = st.selectbox(
        "Select Trend Metric",
        numeric,
        key="trend_metric"
    )

    trend = (
        data.dropna(subset=["Date"])
        .groupby("Date")[trend_metric]
        .sum()
        .sort_index()
    )

    if not trend.empty:
        st.line_chart(trend)

st.success("Mutual Fund Data Analysis Completed!")

st.caption(
    "Always verify source data, currency and units before using analysis."
)
