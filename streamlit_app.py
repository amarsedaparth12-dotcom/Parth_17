
import streamlit as st
import pandas as pd
import io
import re
import requests
# --------------------------------------------------
# PAGE SETTINGS
# --------------------------------------------------

st.set_page_config(
    page_title="Parth | Mutual Fund Analytics",
    page_icon="📊",
    layout="wide"
)

# --------------------------------------------------
# DESIGN / CSS
# --------------------------------------------------

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
    padding: 32px;
    border-radius: 16px;
    color: white;
    margin-bottom: 25px;
}

.main-header h1 {
    color: white;
    font-size: 48px;
    font-weight: 800;
    margin: 0;
}

.main-header h2 {
    color: white;
    font-size: 27px;
    margin: 5px 0 12px 0;
}

.main-header p {
    color: #dceaff;
    font-size: 17px;
}

.section-title {
    color: #082b5c;
    font-size: 25px;
    font-weight: 750;
    margin-top: 20px;
    margin-bottom: 15px;
}

div[data-testid="stMetric"] {
    background: white;
    padding: 18px;
    border-radius: 12px;
    border: 1px solid #dce5f5;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.feature-card {
    background: white;
    border: 1px solid #dce5f5;
    border-radius: 12px;
    padding: 17px;
    min-height: 90px;
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

# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.markdown("""
<div class="main-header">
    <h1>📊 Parth</h1>
    <h2>Mutual Fund Data Analytics Tool</h2>
    <p>Upload raw mutual fund data to clean, format and analyse it.</p>
    <p>📈 Smarter Analysis | Better Decisions</p>
</div>
""", unsafe_allow_html=True)

# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def standardize_column(name):
    name = str(name).strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")


ALIASES = {
    "fund_name": [
        "fund_name", "fund", "scheme_name", "scheme",
        "mutual_fund", "name"
    ],
    "date": [
        "date", "as_of_date", "nav_date", "trade_date"
    ],
    "nav": [
        "nav", "nav_price", "nav_value", "price"
    ],
    "aum": [
        "aum", "aum_usd_million", "assets_under_management",
        "total_assets"
    ],
    "inflow": [
        "inflow", "inflows", "gross_inflow", "subscription"
    ],
    "outflow": [
        "outflow", "outflows", "redemption", "gross_outflow"
    ],
    "net_flow": [
        "net_flow", "net_flows", "net_fund_flow"
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
        "daily_return", "return", "return_percent", "daily_return_percent"
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
            if alias in df.columns:
                rename_map[alias] = standard
                break

    df = df.rename(columns=rename_map)

    df = df.dropna(how="all")
    df = df.drop_duplicates()

    # Convert date
    if "date" in df.columns:
        df["date"] = pd.to_datetime(
            df["date"], errors="coerce"
        )

    # Convert numeric columns
    numeric_columns = [
        "nav", "aum", "inflow", "outflow", "net_flow",
        "daily_return", "expense_ratio", "invested_value",
        "current_value", "units"
    ]

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "", regex=False)
                .str.replace("$", "", regex=False)
                .str.replace("%", "", regex=False),
                errors="coerce"
            )

    # Calculate net flow if possible
    if "net_flow" not in df.columns:
        if "inflow" in df.columns and "outflow" in df.columns:
            df["net_flow"] = df["inflow"] - df["outflow"]

    # Calculate gain/loss if possible
    if "invested_value" in df.columns and "current_value" in df.columns:
        df["gain_loss"] = (
            df["current_value"] - df["invested_value"]
        )

    return df


def make_excel(cleaned, summary):
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        cleaned.to_excel(
            writer, sheet_name="Cleaned Data", index=False
        )
        summary.to_excel(
            writer, sheet_name="Summary", index=False
        )

    output.seek(0)
    return output.getvalue()


# --------------------------------------------------
# FILE UPLOAD
# --------------------------------------------------

st.markdown(
    '<div class="section-title">📂 Upload Mutual Fund Raw Data</div>',
    unsafe_allow_html=True
)

uploaded_file = st.file_uploader(
    "Upload your Excel or CSV file",
    type=["xlsx", "xls", "csv"],
    help="Upload mutual fund raw data for cleaning and analysis."
)

if uploaded_file is None:

    st.info("Upload your Excel or CSV file to begin.")

    st.markdown(
        '<div class="section-title">⭐ Tool Features</div>',
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="feature-card">📁 Raw Data Upload</div>
        <div class="feature-card">🧹 Automatic Data Cleaning</div>
        <div class="feature-card">📋 Column Standardisation</div>
        <div class="feature-card">📊 NAV and AUM Analysis</div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="feature-card">💰 Fund Flow Analysis</div>
        <div class="feature-card">🌎 Country-wise Analysis</div>
        <div class="feature-card">🏭 Sector-wise Analysis</div>
        <div class="feature-card">📥 Excel and CSV Download</div>
        """, unsafe_allow_html=True)

    st.caption("Parth | Mutual Fund Data Analytics")
    st.stop()


# --------------------------------------------------
# READ FILE
# --------------------------------------------------

try:
    if uploaded_file.name.lower().endswith(".csv"):
        raw_data = pd.read_csv(uploaded_file)
    else:
        raw_data = pd.read_excel(uploaded_file)

    cleaned_data = clean_data(raw_data)

except Exception as e:
    st.error(f"Unable to read this file: {e}")
    st.stop()


# --------------------------------------------------
# DATA OVERVIEW
# --------------------------------------------------

st.success("File uploaded and processed successfully!")

st.markdown(
    '<div class="section-title">📊 Data Overview</div>',
    unsafe_allow_html=True
)

c1, c2, c3, c4 = st.columns(4)

c1.metric("Raw Rows", f"{len(raw_data):,}")
c2.metric("Clean Rows", f"{len(cleaned_data):,}")
c3.metric("Columns", f"{len(cleaned_data.columns):,}")
c4.metric(
    "Duplicate Rows Removed",
    f"{len(raw_data.dropna(how='all').drop_duplicates()) - len(cleaned_data):,}"
)


# --------------------------------------------------
# TABS
# --------------------------------------------------

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Cleaned Data",
    "NAV & AUM",
    "Fund Flows",
    "Sector & Country",
    "Download Reports"
])


# --------------------------------------------------
# TAB 1 - CLEANED DATA
# --------------------------------------------------

with tab1:

    st.subheader("Cleaned and Standardised Data")

    st.dataframe(
        cleaned_data,
        use_container_width=True,
        height=420
    )

    st.write("Column names detected:")
    st.write(", ".join(cleaned_data.columns))


# --------------------------------------------------
# TAB 2 - NAV AND AUM
# --------------------------------------------------

with tab2:

    st.subheader("NAV and AUM Analysis")

    if "nav" in cleaned_data.columns:

        st.write("NAV Statistics")
        st.dataframe(
            cleaned_data["nav"].describe().to_frame(),
            use_container_width=True
        )

        if "fund_name" in cleaned_data.columns:
            nav_chart = cleaned_data[
                ["fund_name", "nav"]
            ].dropna()

            st.write("NAV by Fund")
            st.bar_chart(
                nav_chart.set_index("fund_name")
            )

    else:
        st.warning("NAV column was not found in your uploaded data.")

    if "aum" in cleaned_data.columns:

        st.write("AUM Statistics")
        st.dataframe(
            cleaned_data["aum"].describe().to_frame(),
            use_container_width=True
        )

        if "fund_name" in cleaned_data.columns:
            aum_chart = cleaned_data[
                ["fund_name", "aum"]
            ].dropna()

            st.write("AUM by Fund")
            st.bar_chart(
                aum_chart.set_index("fund_name")
            )

    else:
        st.warning("AUM column was not found in your uploaded data.")


# --------------------------------------------------
# TAB 3 - FUND FLOWS
# --------------------------------------------------

with tab3:

    st.subheader("Mutual Fund Flow Analysis")

    if "net_flow" in cleaned_data.columns:

        total_flow = cleaned_data["net_flow"].sum()

        col1, col2 = st.columns(2)

        col1.metric("Total Net Flow", f"{total_flow:,.2f}")
        col2.metric(
            "Average Net Flow",
            f"{cleaned_data['net_flow'].mean():,.2f}"
        )

        if "fund_name" in cleaned_data.columns:

            flow_by_fund = (
                cleaned_data.groupby("fund_name")["net_flow"]
                .sum()
                .sort_values(ascending=False)
            )

            st.write("Net Flow by Fund")
            st.bar_chart(flow_by_fund)

        if "date" in cleaned_data.columns:

            flow_by_date = (
                cleaned_data.dropna(subset=["date"])
                .groupby("date")["net_flow"]
                .sum()
                .sort_index()
            )

            st.write("Date-wise Net Flow")
            st.line_chart(flow_by_date)

    else:
        st.warning(
            "Net Flow could not be calculated. "
            "Your data needs a Net Flow column or both Inflow and Outflow columns."
        )


# --------------------------------------------------
# TAB 4 - SECTOR AND COUNTRY
# --------------------------------------------------

with tab4:

    st.subheader("Sector-wise and Country-wise Analysis")

    col1, col2 = st.columns(2)

    with col1:

        st.write("Sector Analysis")

        if "sector" in cleaned_data.columns:

            sector_counts = (
                cleaned_data["sector"]
                .dropna()
                .value_counts()
            )

            st.bar_chart(sector_counts)

        else:
            st.info("Sector column not found.")

    with col2:

        st.write("Country Analysis")

        if "country" in cleaned_data.columns:

            country_counts = (
                cleaned_data["country"]
                .dropna()
                .value_counts()
            )

            st.bar_chart(country_counts)

        else:
            st.info("Country column not found.")


# --------------------------------------------------
# TAB 5 - DOWNLOAD
# --------------------------------------------------

with tab5:

    st.subheader("Download Your Reports")

    st.download_button(
        label="📥 Download Cleaned CSV",
        data=cleaned_data.to_csv(index=False).encode("utf-8"),
        file_name="Parth_Cleaned_Mutual_Fund_Data.csv",
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

    excel_file = make_excel(cleaned_data, summary)

    st.download_button(
        label="📥 Download Excel Analysis Report",
        data=excel_file,
        file_name="Parth_Mutual_Fund_Analysis.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.write("Analysis Summary")
    st.dataframe(summary, use_container_width=True)


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.markdown("---")
st.caption("© Parth | Mutual Fund Data Analytics Tool")
