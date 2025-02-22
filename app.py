import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import pytz
from gtts import gTTS
import os

# ----------------------
# App Configuration
# ----------------------
st.set_page_config(
    page_title="Crypto Reports",
    page_icon="🪙",
    layout="wide"
)

# ----------------------
# Fetch Crypto Data
# ----------------------
@st.cache_data(ttl=60)
def get_crypto_data():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_market_cap=true&include_24hr_vol=true"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching crypto data: {e}")
        return {}

@st.cache_data(ttl=60)
def get_historical_data(crypto_id, days=1):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart/range?vs_currency=usd&from={start_date.timestamp()}&to={end_date.timestamp()}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        return df
    except Exception as e:
        st.error(f"Error fetching historical data: {e}")
        return pd.DataFrame()

# ----------------
# Text-to-Speech
# ----------------
def speak(text):
    try:
        tts = gTTS(text=text, lang='en')
        tts.save("report.mp3")
        st.audio("report.mp3", format="audio/mp3")
        os.remove("report.mp3")
    except Exception as e:
        st.error(f"Error generating speech: {e}")

# ----------------------
# Get User's Time Zone
# ----------------------
def get_user_timezone():
    if "timezone" not in st.session_state:
        st.markdown("""
        <script>
            const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
            window.parent.postMessage({type: "TIMEZONE", data: timezone}, "*");
        </script>
        """, unsafe_allow_html=True)
        return "UTC"
    return st.session_state.timezone

# ----------------------
# Dashboard
# ----------------------
def render_dashboard():
    st.sidebar.title("Crypto Options")
    selected_coin = st.sidebar.selectbox("Select a Coin", ["Bitcoin (BTC)", "Ethereum (ETH)"])

    crypto_data = get_crypto_data()
    if not crypto_data:
        st.error("Unable to load crypto data at this time.")
        return

    if selected_coin == "Bitcoin (BTC)":
        render_coin_details("bitcoin", "Bitcoin", "BTC", crypto_data)
    elif selected_coin == "Ethereum (ETH)":
        render_coin_details("ethereum", "Ethereum", "ETH", crypto_data)

def render_coin_details(coin_id, coin_name, coin_symbol, crypto_data):
    price = crypto_data.get(coin_id, {}).get("usd", None)
    volume = crypto_data.get(coin_id, {}).get("usd_24h_vol", None)
    market_cap = crypto_data.get(coin_id, {}).get("usd_market_cap", None)

    # Round Values
    price = round(price, 2) if price else 0
    volume = round(volume, 2) if volume else 0
    market_cap = round(market_cap, 2) if market_cap else 0

    st.title(f"{coin_name} ({coin_symbol})")

    # Report Generate
    report_text = (
        f"The current price of {coin_name} is ${price:,}. "
        f"The 24-hour trading volume is ${volume:,}, "
        f"and the market capitalization is ${market_cap:,}."
    )

    # Report Display
    st.subheader("Report:")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Price (USD)", value=f"${price:,}")
    with col2:
        st.metric(label="24h Volume (USD)", value=f"${volume:,}")
    with col3:
        st.metric(label="Market Cap (USD)", value=f"${market_cap:,}")

    st.markdown("""
    <style>
        .report-card {
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 1rem;
            margin-top: 1rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .report-card p {
            font-size: 1rem;
            color: #f8fafc;
        }
    </style>
    """, unsafe_allow_html=True)
    st.markdown(f"""
    <div class="report-card">
        <p>{report_text}</p>
    </div>
    """, unsafe_allow_html=True)

    # Listen Button
    if st.button("Listen Report"):
        speak(report_text)

    # Trading Chart Display
    df = get_historical_data(coin_id, days=1)
    if not df.empty:
        user_timezone = get_user_timezone()
        timezone = pytz.timezone(user_timezone)
        df.index = df.index.tz_localize("UTC").tz_convert(timezone)

        st.subheader(f"{coin_name} Price Movement (Last 24 Hours)")
        st.line_chart(df["price"], use_container_width=True)
    else:
        st.error("Unable to load data.")

# ----------------------
# Main Function
# ----------------------
def main():
    render_dashboard()

if __name__ == "__main__":
    main()
