import streamlit as st
import pandas as pd
import altair as alt

# Page Config

st.set_page_config(
    page_title="Afficionado Coffee Roasters Dashboard",
    layout="wide"
)

st.title("Sales Trend & Time-Based Performance Analysis")

# Fixed definitions - applied on the full data, not redefined after filtering

day_order = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday"
]

def time_bucket(hour):
    if 6 <= hour <= 11:
        return "Morning"
    elif 12 <= hour <= 16:
        return "Afternoon"
    elif 17 <= hour <= 21:
        return "Evening"
    else:
        return "Late Hours"

# Load Data (cached so Streamlit does not re-read the Excel file on every filter change)

@st.cache_data
def load_data():
    data = pd.read_excel("Afficionado_Coffee_Roasters.xlsx", sheet_name="Transactions")

    # Feature Engineering (Temporal)

    data["transaction_time"] = pd.to_datetime(
        data["transaction_time"].astype(str), format="%H:%M:%S"
    )

    data["Hour"] = data["transaction_time"].dt.hour

    # The data has no date column, but rows are ordered by day and then time,
    # so a new day starts wherever the time goes backwards.
    # 181 days found = 1 Jan to 30 Jun 2025, so dates are rebuilt from a 1 Jan 2025 start.
    data["DayNumber"] = (
        data["transaction_time"] < data["transaction_time"].shift()
    ).cumsum()

    data["transaction_date"] = pd.Timestamp("2025-01-01") + pd.to_timedelta(
        data["DayNumber"], unit="D"
    )

    data["Revenue"] = data["transaction_qty"] * data["unit_price"]

    data["DayOfWeek"] = data["transaction_date"].dt.day_name()

    data["DayType"] = data["DayOfWeek"].apply(
        lambda d: "Weekend" if d in ["Saturday", "Sunday"] else "Weekday"
    )

    data["TimeBucket"] = data["Hour"].apply(time_bucket)

    return data

df = load_data()

# First and last calendar weeks are partial - weekly charts use full weeks only
week_ends_all = (
    df.set_index("transaction_date")["Revenue"]
    .resample("W")
    .sum()
    .index[1:-1]
)

# Fixed definition - hours when all three stores are trading (7:00 to 17:59).
# Slow hours are only judged inside this window because stores open and close at different times.
full_trading_hours = list(range(7, 18))

# Store trading hours - first and last transaction of each day, typical (median) per store

def to_clock(h):
    minutes = int(round(h * 60))
    return f"{minutes // 60:02d}:{minutes % 60:02d}"

df["TimeHours"] = df["Hour"] + df["transaction_time"].dt.minute / 60

daily_times = df.groupby(["store_location", "DayNumber"])["TimeHours"].agg(["min", "max"])

trading_hours = pd.DataFrame({
    "Typical Open": daily_times["min"].groupby("store_location").median().apply(to_clock),
    "Typical Close": daily_times["max"].groupby("store_location").median().apply(to_clock),
    "Earliest Open": daily_times["min"].groupby("store_location").min().apply(to_clock),
    "Latest Close": daily_times["max"].groupby("store_location").max().apply(to_clock)
})

# Filters

st.sidebar.header("Filters")

store_filter = st.sidebar.selectbox(
    "Store Location",
    ["All"] + sorted(df["store_location"].unique())
)

day_filter = st.sidebar.multiselect(
    "Day of Week",
    day_order,
    default=day_order
)

hour_filter = st.sidebar.slider(
    "Hour Range",
    int(df["Hour"].min()),
    int(df["Hour"].max()),
    (int(df["Hour"].min()), int(df["Hour"].max()))
)

metric_filter = st.sidebar.radio(
    "Metric",
    ["Revenue", "Quantity"]
)

if metric_filter == "Revenue":
    metric_col = "Revenue"
else:
    metric_col = "transaction_qty"

# Apply Filters

filtered_df = df.copy()

if store_filter != "All":
    filtered_df = filtered_df[
        filtered_df["store_location"] == store_filter
    ]

filtered_df = filtered_df[
    filtered_df["DayOfWeek"].isin(day_filter)
]

filtered_df = filtered_df[
    (filtered_df["Hour"] >= hour_filter[0])
    &
    (filtered_df["Hour"] <= hour_filter[1])
]

# Guard against empty filter results

if filtered_df.empty:
    st.warning("No transactions match the selected filters. Try adjusting them.")
    st.stop()

# Overall Sales Trend Dashboard

st.header("Overall Sales Trend Dashboard")

total_revenue = filtered_df["Revenue"].sum()

total_transactions = filtered_df["transaction_id"].nunique()

total_quantity = filtered_df["transaction_qty"].sum()

avg_revenue_per_transaction = total_revenue / total_transactions

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Total Revenue",
    round(total_revenue, 2)
)

col2.metric(
    "Total Transactions",
    total_transactions
)

col3.metric(
    "Total Quantity Sold",
    total_quantity
)

col4.metric(
    "Avg Revenue per Transaction",
    round(avg_revenue_per_transaction, 2)
)

st.subheader(f"Daily {metric_filter} Trend")

daily_trend = (
    filtered_df
    .groupby("transaction_date")[metric_col]
    .sum()
)

st.line_chart(daily_trend)

st.subheader(f"Weekly {metric_filter} Trend")

weekly_trend = (
    filtered_df
    .set_index("transaction_date")[metric_col]
    .resample("W")
    .sum()
)

weekly_trend = weekly_trend[weekly_trend.index.isin(week_ends_all)]

st.line_chart(weekly_trend)

st.subheader(f"Weekly {metric_filter} Trend by Store")

store_weekly_trend = (
    filtered_df
    .groupby([pd.Grouper(key="transaction_date", freq="W"), "store_location"])[metric_col]
    .sum()
    .unstack()
)

store_weekly_trend = store_weekly_trend[store_weekly_trend.index.isin(week_ends_all)]

st.line_chart(store_weekly_trend)

# Day-of-Week Performance

st.header("Day-of-Week Performance")

# daily totals first, then average per day of week

daily_totals = (
    filtered_df
    .groupby(["transaction_date", "DayOfWeek", "DayType"])
    .agg(
        MetricTotal=(metric_col, "sum"),
        Transactions=("transaction_id", "nunique")
    )
    .reset_index()
)

dow_summary = (
    daily_totals
    .groupby("DayOfWeek")[["MetricTotal", "Transactions"]]
    .mean()
    .reindex(day_order)
    .dropna()
    .reset_index()
)

col1, col2 = st.columns(2)

col1.subheader(f"Average {metric_filter} by Day")

col1.altair_chart(
    alt.Chart(dow_summary).mark_bar().encode(
        x=alt.X("DayOfWeek", sort=day_order, title="Day"),
        y=alt.Y("MetricTotal", title=f"Avg {metric_filter}")
    ).properties(width="container")
)

col2.subheader("Average Transactions by Day")

col2.altair_chart(
    alt.Chart(dow_summary).mark_bar().encode(
        x=alt.X("DayOfWeek", sort=day_order, title="Day"),
        y=alt.Y("Transactions", title="Avg Transactions")
    ).properties(width="container")
)

st.subheader("Weekday vs Weekend")

daytype_summary = (
    daily_totals
    .groupby("DayType")[["MetricTotal", "Transactions"]]
    .mean()
)

st.dataframe(daytype_summary)

# Time-of-Day Demand Analysis

st.header("Time-of-Day Demand Analysis")

hourly_summary = (
    filtered_df
    .groupby("Hour")
    .agg(
        Transactions=("transaction_id", "nunique"),
        MetricTotal=(metric_col, "sum")
    )
)

st.caption(
    "Stores open and close at different times (see Location Comparison Panel), "
    "so totals at 6 AM and after 6 PM reflect trading hours, not just demand."
)

col1, col2 = st.columns(2)

col1.subheader("Hourly Transaction Volume")
col1.line_chart(hourly_summary["Transactions"])

col2.subheader(f"Hourly {metric_filter} Distribution")
col2.bar_chart(hourly_summary["MetricTotal"])

st.subheader(f"{metric_filter} by Time Bucket")

bucket_summary = (
    filtered_df
    .groupby("TimeBucket")[metric_col]
    .sum()
)

bucket_share = bucket_summary / bucket_summary.sum() * 100

st.dataframe(
    pd.DataFrame({
        metric_filter: bucket_summary,
        "Share %": bucket_share.round(2)
    })
)

# Hourly Demand Heatmaps

st.header("Hourly Demand Heatmaps")

def hourly_heatmap(data):
    heat = (
        data
        .groupby(["DayOfWeek", "Hour"])[metric_col]
        .sum()
        .reset_index()
    )
    return alt.Chart(heat).mark_rect().encode(
        x=alt.X("Hour:O", title="Hour of Day"),
        y=alt.Y("DayOfWeek:N", sort=day_order, title="Day"),
        color=alt.Color(f"{metric_col}:Q", title=metric_filter)
    ).properties(width="container")

st.subheader("All Selected Stores")
st.altair_chart(hourly_heatmap(filtered_df))

for store in sorted(filtered_df["store_location"].unique()):
    st.subheader(store)
    st.altair_chart(
        hourly_heatmap(filtered_df[filtered_df["store_location"] == store])
    )

# Location Comparison Panel

st.header("Location Comparison Panel")

store_totals = (
    filtered_df
    .groupby("store_location")[metric_col]
    .sum()
)

st.subheader(f"Total {metric_filter} by Store")
st.bar_chart(store_totals)

store_hourly = (
    filtered_df
    .groupby(["Hour", "store_location"])[metric_col]
    .sum()
    .unstack()
)

st.subheader(f"Hourly {metric_filter} by Store")
st.line_chart(store_hourly)

st.caption("Hours outside a store's trading hours show low or zero values.")

peak_hour_by_store = store_hourly.idxmax()

store_summary = pd.DataFrame({
    f"Total {metric_filter}": store_totals,
    "Peak Hour": peak_hour_by_store
})

st.subheader("Peak Hour by Store")
st.dataframe(store_summary)

st.subheader("Store Trading Hours")
st.caption("Based on the first and last transaction of each day across the full data.")
st.dataframe(trading_hours)

# Peak & Slow Period Finder

st.header("Peak & Slow Period Finder")

busiest_day = dow_summary.loc[dow_summary["MetricTotal"].idxmax(), "DayOfWeek"]
slowest_day = dow_summary.loc[dow_summary["MetricTotal"].idxmin(), "DayOfWeek"]

peak_hour = hourly_summary["Transactions"].idxmax()

# slowest hour is only judged while all three stores are trading
trading_window = hourly_summary[hourly_summary.index.isin(full_trading_hours)]

if len(trading_window) > 0:
    slowest_hour_label = f"{trading_window['Transactions'].idxmin()}:00"
else:
    slowest_hour_label = "n/a"

peak_bucket = bucket_summary.idxmax()

weekday_avg = daily_totals[daily_totals["DayType"] == "Weekday"]["MetricTotal"].mean()
weekend_avg = daily_totals[daily_totals["DayType"] == "Weekend"]["MetricTotal"].mean()

if pd.notna(weekday_avg) and weekday_avg != 0 and pd.notna(weekend_avg):
    weekend_weekday_ratio = weekend_avg / weekday_avg
else:
    weekend_weekday_ratio = 0

st.caption(
    "Over the full data, differences between days are small and not statistically "
    "significant (see notebook), so busiest and slowest day should be read with care."
)

col1, col2, col3 = st.columns(3)

col1.metric("Busiest Day", busiest_day)
col2.metric("Slowest Day", slowest_day)
col3.metric("Peak Time Bucket", peak_bucket)

col4, col5, col6 = st.columns(3)

col4.metric("Peak Hour", f"{peak_hour}:00")
col5.metric("Slowest Hour (7 AM-6 PM)", slowest_hour_label)
col6.metric("Weekend / Weekday Ratio", round(weekend_weekday_ratio, 2))

# Filtered Dataset

st.header("Filtered Dataset")

st.dataframe(filtered_df)
