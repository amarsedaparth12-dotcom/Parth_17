
import io
import re
import requests
import pandas as pd
import streamlit as st

# =====================================================
# PAGE SETTINGS
# =====================================================

st.set_page_config(
    page_title="Parth | Mutual Fund Analytics",
    page_icon="📊",
    layout="wide"
)

ETFIQ_URL = "https://etfiq.com/data/flows/daily/latest.csv"

# =====================================================
# DESIGN
# =====================================================

st.markdown("""
<style>
.stApp {
    background: #f4f7fc;
}
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}
.main-header {
    background: linear-gradient(110deg, #001b46, #0755a5);
    padding: 30px;
    border-radius: 16px;
    color: white;
    margin-bottom: 25px;
}
.main-header h1 {
    color: white;
    font-size: 42px;
    margin: 0;
}
.main-header h2 {
    color: white;
    font-size: 24px;
    margin: 8px 0;
}
.main-header p {
    color: #dceaff;
}
.section-title {
    color: #082b5c;
    font-size: 24px;
    font-weight: 750;
    margin-top: 20px;
    margin-bottom: 12px;
}
div[data-testid="stMetric"] {
    background: white;
    padding: 16px;
    border-radius: 12px;
    border: 1px solid #dce5f5;
}
.feature-card {
    background: white;
    border: 1px solid #dce5f5;
    border-radius: 12px;
    padding: 17px;
    min-height: 65px;
    margin-bottom: 10px;
    color: #12345c;
    font-weight: 600;
}
.stButton button {
    background: #0755a5;
    color: white;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# HEADER
# =====================================================

st.markdown("""
<div class="main-header">
    <h1>📊 Parth</h1>
    <h2>Mutual Fund & ETF Data Analytics Tool</h2>
    <p>Upload your data or fetch daily ETF flows automatically.</p>
    <p>📈 Smarter Analysis | Better Decisions</p>
</div>
""", unsafe_allow_html=True)

# =====================================================
# COLUMN STANDARDISATION
# =====================================================

def standardize_column(name):
    name = str(name).strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")


ALIASES = {
    "fund_name": [
        "fund_name", "fund", "scheme_name", "scheme",
        "mutual_fund", "etf_name", "name"
    ],
    "ticker": [
        "ticker", "symbol", "stock_symbol", "etf_ticker"
    ],
    "date": [
        "date", "as_of_date", "nav_date", "trade_date",
        "flow_date", "report_date"
    ],
    "nav": [
        "nav", "nav_price", "nav_value", "price",
        "market_price", "close"
    ],
    "aum": [
        "aum", "aum_usd", "assets", "net_assets",
        "total_assets", "assets_under_management"
    ],
    "inflow": [
        "inflow", "inflows", "gross_inflow", "subscription"
    ],
    "outflow": [
        "outflow", "outflows", "redemption", "gross_outflow"
    ],
    "net_flow": [
        "net_flow", "net_flows", "net_fund_flow",
        "fund_flow", "fund_flows", "daily_flow",
        "daily_flows", "flow", "flows",
        "estimated_flow", "flow_usd", "fund_flow_usd"
    ],
    "category": [
        "category", "fund_category", "fund_type", "asset_class"
    ],
    "country": [
        "country", "country_region", "region", "market"
    ],
    "sector": [
        "sector", "sector_focus", "industry"
    ],
    "daily_return": [
        "daily_return", "return", "return_percent",
        "daily_return_percent"
    ],
    "expense_ratio": [
        "expense_ratio", "expense_ratio_percent"
    ],
    "benchmark": [
        "benchmark", "benchmark_index"
    ],
    "invested_value": [
        "invested_value", "investment", "cost_value"
    ],
    "current_value": [
        "current_value", "market_value", "holding_value"
    ],
    "units": [
        "units", "quantity", "shares"
    ]
}


def clean_data(raw):
    df = raw.copy()

    df.columns = [standardize_column(c) for c in df.columns]

    rename_map = {}

    for standard, aliases in ALIASES.items():
        for alias in aliases:
            if alias in df.columns and standard not in df.columns:
                rename_map[alias] = standard
                break

    df = df.rename(columns=rename_map)

    df = df.dropna(how="all")
    df = df.drop_duplicates()

    if "date" in df.columns:
        df["date"] = pd.to_datetime(
            df["date"], errors="coerce"
        )

    numeric_columns = [
        "nav", "aum", "inflow", "outflow", "net_flow",
        "daily_return", "expense_ratio",
        "invested_value", "current_value", "units"
    ]

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str)
                .str.replace(",", "", regex=False)
                .str.replace("$", "", regex=False)
                .str.replace("%", "", regex=False),
                errors="coerce"
            )

    if (
        "net_flow" not in df.columns
        and "inflow" in df.columns
        and "outflow" in df.columns
    ):
        df["net_flow"] = df["inflow"] - df["outflow"]

    if (
        "invested_value" in df.columns
        and "current_value" in df.columns
    ):
        df["gain_loss"] = (
            df["current_value"] - df["invested_value"]
        )

    return df


# =====================================================
# ETFIQ AUTOMATIC DATA FETCH
# =====================================================

def fetch_etfiq_data():
    response = requests.get(
        ETFIQ_URL,
        headers={
            "User-Agent": "Mozilla/5.0 ParthAnalytics/1.0"
        },
        timeout=40
    )

    response.raise_for_status()

    if not response.content:
        raise ValueError("The website returned an empty file.")

    df = pd.read_csv(io.BytesIO(response.content))

    if df.empty:
        raise ValueError("No ETFIQ records were found.")

    return df


# =====================================================
# DATA SOURCE SELECTION
# =====================================================

st.markdown(
    '<div class="section-title">🌐 Select Your Data Source</div>',
    unsafe_allow_html=True
)

source = st.radio(
    "Choose how you want to add data:",
    ["Automatic ETFIQ Fetch", "Manual Excel / CSV Upload"],
    horizontal=True
)

raw_data = None
source_name = ""

if source == "Automatic ETFIQ Fetch":

    st.info(
        "Fetch the latest available US ETF daily fund-flow "
        "data directly from ETFIQ."
    )

    st.caption("Source: https://etfiq.com/data/")

    if st.button("🔄 Fetch Latest ETFIQ Data", type="primary"):

        try:
            with st.spinner("Fetching data from ETFIQ..."):
                fetched_data = fetch_etfiq_data()

            st.session_state["etfiq_raw_data"] = fetched_data
            st.success(
                f"Successfully fetched {len(fetched_data):,} records!"
            )

        except Exception as error:
            st.error(f"ETFIQ data fetch failed: {error}")

    if "etfiq_raw_data" in st.session_state:
        raw_data = st.session_state["etfiq_raw_data"]
        source_name = "ETFIQ Daily ETF Flows"

else:

    uploaded_file = st.file_uploader(
        "Upload your Excel or CSV file",
        type=["xlsx", "xls", "csv"],
        help="Upload mutual fund or ETF raw data."
    )

    if uploaded_file is not None:
        try:
            if uploaded_file.name.lower().endswith(".csv"):
                raw_data = pd.read_csv(uploaded_file)
            elif uploaded_file.name.lower().endswith(".xls"):
                raw_data = pd.read_excel(
                    uploaded_file, engine="xlrd"
                )
            else:
                raw_data = pd.read_excel(uploaded_file)

            source_name = uploaded_file.name

        except Exception as error:
            st.error(f"Unable to read your file: {error}")


# =====================================================
# SHOW EMPTY STATE
# =====================================================

if raw_data is None:

    st.markdown(
        '<div class="section-title">⭐ Tool Features</div>',
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="feature-card">📁 Excel / CSV Upload</div>
        <div class="feature-card">🧹 Automatic Data Cleaning</div>
        <div class="feature-card">📋 Column Standardisation</div>
        <div class="feature-card">📊 NAV and AUM Analysis</div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="feature-card">🌐 ETFIQ Automatic Fetch</div>
        <div class="feature-card">💰 Fund Flow Analysis</div>
        <div class="feature-card">🌎 Country-wise Analysis</div>
        <div class="feature-card">🏭 Sector-wise Analysis</div>
        <div class="feature-card">📥 Excel and CSV Download</div>
        """, unsafe_allow_html=True)

    st.caption("© Parth | Mutual Fund & ETF Data Analytics")
    st.stop()


# =====================================================
# CLEAN AND PROCESS DATA
# =====================================================

try:
    cleaned_data = clean_data(raw_data)

except Exception as error:
    st.error(f"Data cleaning failed: {error}")
    st.stop()


if cleaned_data.empty:
    st.warning("No usable records were found in this dataset.")
    st.stop()


# =====================================================
# DATA OVERVIEW
# =====================================================

st.success(f"Data loaded successfully from: {source_name}")

st.markdown(
    '<div class="section-title">📊 Data Overview</div>',
    unsafe_allow_html=True
)

c1, c2, c3, c4 = st.columns(4)

c1.metric("Raw Rows", f"{len(raw_data):,}")
c2.metric("Clean Rows", f"{len(cleaned_data):,}")
c3.metric("Total Columns", f"{len(cleaned_data.columns):,}")
c4.metric(
    "Duplicates Removed",
    f"{len(raw_data.dropna(how='all').drop_duplicates()) - len(cleaned_data):,}"
)

st.caption(
    "Note: Values and units are shown as supplied by the data source. "
    "Check the source documentation before interpreting financial amounts."
)


# =====================================================
# ANALYSIS TABS
# =====================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Cleaned Data",
    "NAV & AUM",
    "Fund Flows",
    "Sector & Country",
    "Download Reports"
])


# =====================================================
# TAB 1 - CLEANED DATA
# =====================================================

with tab1:

    st.subheader("Cleaned and Standardised Data")

    st.dataframe(
        cleaned_data,
        use_container_width=True,
        height=420
    )

    st.write("Detected columns:")
    st.write(", ".join(cleaned_data.columns))


# =====================================================
# TAB 2 - NAV AND AUM
# =====================================================

with tab2:

    st.subheader("NAV and AUM Analysis")

    col1, col2 = st.columns(2)

    with col1:

        if "nav" in cleaned_data.columns:

            st.write("NAV Statistics")

            st.dataframe(
                cleaned_data["nav"].describe().to_frame(),
                use_container_width=True
            )

        else:
            st.info("NAV column is not available in this dataset.")

    with col2:

        if "aum" in cleaned_data.columns:

            st.write("AUM Statistics")

            st.dataframe(
                cleaned_data["aum"].describe().to_frame(),
                use_container_width=True
            )

        else:
            st.info("AUM column is not available in this dataset.")

    name_column = (
        "fund_name"
        if "fund_name" in cleaned_data.columns
        else "ticker" if "ticker" in cleaned_data.columns
        else None
    )

    if name_column and "nav" in cleaned_data.columns:

        nav_chart = cleaned_data[
            [name_column, "nav"]
        ].dropna()

        if not nav_chart.empty:
            st.write("NAV by Fund / Ticker")
            st.bar_chart(
                nav_chart.groupby(name_column)["nav"].mean()
            )

    if name_column and "aum" in cleaned_data.columns:

        aum_chart = cleaned_data[
            [name_column, "aum"]
        ].dropna()

        if not aum_chart.empty:
            st.write("AUM by Fund / Ticker")
            st.bar_chart(
                aum_chart.groupby(name_column)["aum"].mean()
            )


# =====================================================
# TAB 3 - FUND FLOWS
# =====================================================

with tab3:

    st.subheader("Fund Flow Analysis")

    if "net_flow" in cleaned_data.columns:

        total_flow = cleaned_data["net_flow"].sum()

        col1, col2 = st.columns(2)

        col1.metric(
            "Total Net Flow (Source Units)",
            f"{total_flow:,.2f}"
        )

        col2.metric(
            "Average Net Flow (Source Units)",
            f"{cleaned_data['net_flow'].mean():,.2f}"
        )

        if name_column:

            flow_by_fund = (
                cleaned_data.groupby(name_column)["net_flow"]
                .sum()
                .sort_values(ascending=False)
            )

            st.write("Net Flow by Fund / Ticker")
            st.bar_chart(flow_by_fund)

        if "date" in cleaned_data.columns:

            flow_by_date = (
                cleaned_data.dropna(subset=["date"])
                .groupby("date")["net_flow"]
                .sum()
                .sort_index()
            )

            if not flow_by_date.empty:
                st.write("Date-wise Net Flow")
                st.line_chart(flow_by_date)

    elif (
        "inflow" in cleaned_data.columns
        and "outflow" in cleaned_data.columns
    ):

        st.info(
            "Net Flow is not supplied, but Inflow and Outflow "
            "columns are available."
        )

        st.metric(
            "Total Inflow",
            f"{cleaned_data['inflow'].sum():,.2f}"
        )

        st.metric(
            "Total Outflow",
            f"{cleaned_data['outflow'].sum():,.2f}"
        )

    else:

        st.warning(
            "No recognised Net Flow, Inflow or Outflow column "
            "was found. Check the raw data column names."
        )


# =====================================================
# TAB 4 - SECTOR AND COUNTRY
# =====================================================

with tab4:

    st.subheader("Sector-wise and Country-wise Analysis")

    col1, col2 = st.columns(2)

    with col1:

        st.write("Sector Analysis")

        if "sector" in cleaned_data.columns:

            if "net_flow" in cleaned_data.columns:
                sector_data = (
                    cleaned_data.groupby("sector")["net_flow"]
                    .sum()
                    .sort_values(ascending=False)
                )
                st.bar_chart(sector_data)
            else:
                st.bar_chart(
                    cleaned_data["sector"].dropna().value_counts()
                )

        else:
            st.info("Sector column not found in this dataset.")

    with col2:

        st.write("Country Analysis")

        if "country" in cleaned_data.columns:

            if "net_flow" in cleaned_data.columns:
                country_data = (
                    cleaned_data.groupby("country")["net_flow"]
                    .sum()
                    .sort_values(ascending=False)
                )
                st.bar_chart(country_data)
            else:
                st.bar_chart(
                    cleaned_data["country"].dropna().value_counts()
                )

        else:
            st.info("Country column not found in this dataset.")


# =====================================================
# TAB 5 - DOWNLOAD REPORTS
# =====================================================

with tab5:

    st.subheader("Download Your Reports")

    csv_data = cleaned_data.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="📥 Download Cleaned CSV",
        data=csv_data,
        file_name="Parth_Cleaned_Data.csv",
        mime="text/csv"
    )

    summary_rows = []

    for col in cleaned_data.select_dtypes(include="number").columns:

        summary_rows.append({
            "Metric": col,
            "Total": cleaned_data[col].sum(),
            "Average": cleaned_data[col].mean(),
            "Minimum": cleaned_data[col].min(),
            "Maximum": cleaned_data[col].max()
        })

    summary = pd.DataFrame(summary_rows)

    output = io.BytesIO()

    try:

        with pd.ExcelWriter(
            output, engine="openpyxl"
        ) as writer:

            cleaned_data.to_excel(
                writer,
                sheet_name="Cleaned Data",
                index=False
            )

            summary.to_excel(
                writer,
                sheet_name="Summary",
                index=False
            )

        output.seek(0)

        st.download_button(
            label="📥 Download Excel Analysis Report",
            data=output.getvalue(),
            file_name="Parth_Data_Analysis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as error:

        st.error(f"Excel report could not be created: {error}")

    st.write("Analysis Summary")
    st.dataframe(summary, use_container_width=True)


# =====================================================
# FOOTER
# =====================================================

st.markdown("---")
st.caption("© Parth | Mutual Fund & ETF Data Analytics Tool")
