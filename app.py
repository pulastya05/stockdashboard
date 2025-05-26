import streamlit as st
from fyers_apiv3 import fyersModel
import pandas as pd
import requests
from io import StringIO
from datetime import datetime, timedelta

@st.cache_data
def load_symbol_list():
    url = "https://public.fyers.in/sym_details/NSE_CM.csv"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = StringIO(response.text)
        symbol_df = pd.read_csv(data, header=None)
        symbol_df.columns = ["fytoken", "name", "segment", "lot_size", "tick_size", "isin", "trading_session",
                             "last_update", "expiry", "symbol", "exchange", "segment_code", "short_name",
                             "strike", "option_type", "fytoken2", "misc", "misc2"] + [f"col{i}" for i in range(18, len(symbol_df.columns))]
        symbol_df = symbol_df[symbol_df["segment"] == 0]
        return symbol_df
    except:
        return pd.DataFrame({
            "symbol": ["NSE:SBIN-EQ", "NSE:INFY-EQ"],
            "name": ["State Bank of India", "Infosys Ltd"]
        })

symbol_df = load_symbol_list()

st.title("📊 Stock Data Dashboard")

search_term = st.text_input("🔍 Search Stock (e.g., Reli)", value="")

if search_term:
    filtered_stocks = symbol_df[symbol_df["name"].str.contains(search_term, case=False, na=False)]
else:
    filtered_stocks = symbol_df

if not filtered_stocks.empty:
    stock_options = filtered_stocks.apply(lambda x: f"{x['name']} ({x['symbol']})", axis=1).tolist()
    selected_stocks = st.multiselect("📌 Select Stock(s)", stock_options)
    selected_symbols = [s.split("(")[-1].strip(")") for s in selected_stocks]
else:
    st.warning("No stocks found.")
    selected_symbols = []

start_date = st.date_input("📅 Start Date", value=datetime(2020, 1, 1))
end_date = st.date_input("📅 End Date", value=datetime.today())

download_mode = st.radio("Download Mode", ["Individually", "Combined"])
include_all = st.checkbox("Download all available stocks (⚠️ May take time)", value=False)

client_id = "MUA5R7UTG0-100"
access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOlsiZDoxIiwiZDoyIiwieDowIiwieDoxIiwieDoyIl0sImF0X2hhc2giOiJnQUFBQUFCb005N2I2dG5FVGEwZnJGTW1aQmxoU3JiX2ZLQkZEZWw4S3pvdWdDLTAwMlN1ZG5zSG1HQlRDY2dyMmFhU3NXWEctQXFnRF9YejROMWJULWZLaGM3WjlTTmJVS1MxbXp6YXhoc1hLdm5QZFZmWTVvTT0iLCJkaXNwbGF5X25hbWUiOiIiLCJvbXMiOiJLMSIsImhzbV9rZXkiOiI1MTFjNTZkMTAwZDdkMDA0NTYyOTEzMGFkZmQwYjEyMDJjNjliZTkzYzY1M2NkNGNkYmU5ZDBkMCIsImlzRGRwaUVuYWJsZWQiOiJOIiwiaXNNdGZFbmFibGVkIjoiTiIsImZ5X2lkIjoiWVIyMzA3NCIsImFwcFR5cGUiOjEwMCwiZXhwIjoxNzQ4MzA1ODAwLCJpYXQiOjE3NDgyMjk4NTEsImlzcyI6ImFwaS5meWVycy5pbiIsIm5iZiI6MTc0ODIyOTg1MSwic3ViIjoiYWNjZXNzX3Rva2VuIn0.4mMiiU-d98levxu7Qzcev80iaSuYQb-MZ-ShNhW15bI"  # Replace with your token
fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, log_path="")

def fetch_historical_data(symbol, start, end, interval="D"):
    all_data = []
    current_start = start
    while current_start <= end:
        chunk_end = min(current_start + timedelta(days=100), end)
        data = {
            "symbol": symbol,
            "resolution": interval,
            "date_format": "1",
            "range_from": current_start.strftime("%Y-%m-%d"),
            "range_to": chunk_end.strftime("%Y-%m-%d"),
            "cont_flag": "1"
        }
        response = fyers.history(data=data)
        if "candles" in response and response["candles"]:
            all_data.extend(response["candles"])
        current_start = chunk_end + timedelta(days=1)
    if all_data:
        df = pd.DataFrame(all_data, columns=["date", "open", "high", "low", "close", "volume"])
        df["date"] = pd.to_datetime(df["date"], unit="s")
        df.insert(0, "symbol", symbol)
        return df
    return None

if st.button("📥 Fetch & Download"):
    if start_date > end_date:
        st.error("Start date must be before end date.")
    else:
        symbols_to_download = [s for s in symbol_df["symbol"].unique()] if include_all else selected_symbols
        if not symbols_to_download:
            st.warning("⚠️ Please select at least one stock or enable 'Download all'.")
        else:
            all_data = []
            with st.spinner("Fetching data..."):
                for symbol in symbols_to_download:
                    df = fetch_historical_data(symbol, start_date, end_date)
                    if df is not None:
                        st.success(f"✅ Data fetched for {symbol}")
                        all_data.append(df)
                        if download_mode == "Individually":
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label=f"Download {symbol.replace(':', '_')}.csv",
                                data=csv,
                                file_name=f"{symbol.replace(':', '_')}_{start_date}_{end_date}.csv",
                                mime="text/csv"
                            )
                    else:
                        st.warning(f"⚠️ No data found for {symbol}")
            if download_mode == "Combined" and all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                csv = combined_df.to_csv(index=False)
                st.download_button(
                    label="📦 Download Combined CSV",
                    data=csv,
                    file_name=f"Combined_Stock_Data_{start_date}_{end_date}.csv",
                    mime="text/csv"
                )
