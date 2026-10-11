# Sales Trend and Time-Based Performance Analysis - Afficionado Coffee Roasters

Time-based sales analytics for a specialty coffee retailer with three New York stores (Astoria, Hell's Kitchen, Lower Manhattan). The project shows **when** sales happen, so managers can plan staffing and operating hours with data instead of intuition.

## Business Problem

Managers rely on intuition ("mornings are busy") to schedule staff. Without a consolidated view of sales over time, the business risks overstaffing slow hours, understaffing rush periods, and running inefficiently. This project answers:

- How have sales trended across 2025?
- Which days of the week are busiest and slowest?
- Which hours are the peak transaction hours?
- How do demand patterns differ between store locations?

## Project Structure

```
.
├── coffee_analysis.ipynb                # EDA and analysis notebook
├── coffee_app.py                        # Streamlit dashboard
├── Afficionado_Coffee_Roasters.xlsx     # Dataset (sheet: Transactions) - add this file yourself
├── requirements.txt
└── README.md
```

## Dataset

149,116 transaction rows, one sheet named `Transactions`.

| Column | Description |
|---|---|
| transaction_id | Unique identifier per transaction |
| year | Transaction year (2025) |
| transaction_time | Time of transaction (HH:MM:SS) |
| transaction_qty | Quantity purchased |
| unit_price | Price per unit |
| store_id | Store identifier |
| store_location | Physical store location |
| product_id | Unique identifier for each product |
| product_category | Broad product group |
| product_type | Product variant within the category |
| product_detail | Detailed attributes such as flavor or blend |

### Important: dates are reconstructed

The dataset has **no date column**. Rows are ordered by day and then by time, so a new day starts wherever the time goes backwards. This produces exactly 181 days (1 Jan to 30 Jun 2025), and every day starts in the morning and ends in the evening. Dates are rebuilt assuming the data **starts on 1 Jan 2025**.

- Hourly, store and time-bucket results do not depend on this assumption.
- Day-of-week labels do. If the real start date is different, the labels shift.

### Important: stores trade different hours

Based on the first and last transaction of each day:

| Store | Typical open | Typical close (last transaction) |
|---|---|---|
| Astoria | 07:04 | 19:57 |
| Hell's Kitchen | 06:37 | 19:57 (occasionally as late as about 21:00) |
| Lower Manhattan | 06:18 | 18:27 (varies a lot by day) |

Hourly totals at 6 AM and after 6 PM therefore reflect store hours, not just demand. Only 7:00-17:59 has all three stores trading, so slow hours are judged in that window.

## Methodology

1. **Data ingestion and validation:** missing values, duplicates, duplicate transaction IDs, timestamp format, positive quantities and prices, and store trading hours.
2. **Feature engineering:** revenue per transaction (`transaction_qty * unit_price`), hour of day, day of week, weekday/weekend flag, and time buckets (Morning 6-11, Afternoon 12-16, Evening 17-21, Late Hours 22-5).
3. **Sales trend analysis:** daily and weekly revenue, week-over-week change, store-level trends. Partial first and last calendar weeks are excluded from weekly views.
4. **Day-of-week performance:** average revenue and transactions by day, weekday vs weekend. Because sales grow over the period, each day is also compared with its own week and tested for significance (Kruskal-Wallis, Mann-Whitney).
5. **Time-of-day demand:** hourly volume and revenue, time-bucket shares, rush and slow hours.
6. **Cross-location comparison:** hourly curves, peak hour and day-by-hour heatmaps per store.

## Key Findings

- Weekly revenue roughly doubles over the period (about 18-20k to about 38-41k). The growth is volume, not price: transactions per day roughly double (about 560 to about 1,180) while the average transaction value stays at 4.71. All three stores grow by about the same factor (2.0-2.1x).
- Day of week does not meaningfully affect demand. Raw day averages differ by about 3%, and after removing the growth trend the difference is not statistically significant (Kruskal-Wallis p = 0.55; weekday vs weekend p = 0.26).
- Demand peaks from 8 to 10 AM, with 10 AM the busiest hour at all three stores. Mornings bring in about 56% of revenue. After 11 AM demand roughly halves and stays flat until 6 PM, so there is no evening peak.
- Hell's Kitchen and Lower Manhattan have sharp morning peaks. Astoria's morning peak is smaller, but its afternoon demand is the highest and stays steady until its 8 PM close.
- Lower Manhattan's weak evenings (about 8% of revenue) mostly come from closing earlier, around 6:30 PM, not from weaker demand while open. Astoria has the strongest evenings (about 21%) because it trades steadily until 8 PM.
- There are no transactions between 10 PM and 5 AM because the stores are closed, so the Late Hours bucket is empty.

## Streamlit Dashboard

**Modules:** overall sales trend, day-of-week performance, hourly demand heatmaps (all stores and per store), location comparison panel (including store trading hours), and a peak and slow period finder.

**Sidebar controls:** store location, day-of-week selector, hour-range slider, revenue vs quantity toggle.

## How to Run

```bash
# 1. Install dependencies (Python 3.10+ recommended)
pip install -r requirements.txt

# 2. Put Afficionado_Coffee_Roasters.xlsx in the same folder as the code

# 3. Open the notebook
jupyter notebook coffee_analysis.ipynb

# 4. Launch the dashboard
streamlit run coffee_app.py
```

## Deliverables

- Research paper (EDA, insights, recommendations)
- Streamlit dashboard (live analytics)
- Executive summary for stakeholders

## Tech Stack

Python, pandas, scipy, seaborn, matplotlib, altair, Streamlit, Jupyter.
