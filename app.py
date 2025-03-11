import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import requests
from datetime import datetime, timedelta
import json
import pyttsx3
import pytz

# ------------------
# App Configuration
# ------------------
st.set_page_config(
    page_title="Crypto Reports",
    page_icon="🪙",
    layout="wide"
)

# ---------------
# Load User Data
# ---------------
def load_users():
    try:
        with open("user.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("User data file not found.")
        return {}
    except Exception as e:
        st.error(f"Error loading user data: {e}")
        return {}

# ---------------
# Authentication
# ---------------
def authenticate(username, password):
    users = load_users()
    if username in users and users[username] == password:
        return True
    return False

# ------------------
# Fetch Crypto Data
# ------------------
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

# ---------------
# Text-to-Speech
# ---------------
def speak(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    engine.say(text)
    engine.runAndWait()

# ---------------------
# Get User's Time Zone
# ---------------------
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

# -----------
# Login Page
# -----------
def show_login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if authenticate(username, password):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Invalid credentials")

# --------------------
# Dashboard
# --------------------
def render_dashboard():
    st.sidebar.title("Crypto Options")
    selected_coin = st.sidebar.selectbox("Select a Coin", ["Bitcoin (BTC)", "Ethereum (ETH)"])

    # Log Out Button
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

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
    with st.container():
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

    # Listen and Stop buttons
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Listen Report"):
            st.session_state.speaking = True
            speak(report_text)
            st.session_state.speaking = False
    with col2:
        if st.button("Stop Reading"):
            st.session_state.speaking = False
            pyttsx3.init().stop()

    # Trading Chart Display
    df = get_historical_data(coin_id, days=1)
    if not df.empty:
        # For Time Zone
        user_timezone = get_user_timezone()
        timezone = pytz.timezone(user_timezone)
        df.index = df.index.tz_localize("UTC").tz_convert(timezone)

        # For Dynamic Coloring
        df["price_diff"] = df["price"].diff()
        up_indices = df[df["price_diff"] > 0].index
        down_indices = df[df["price_diff"] < 0].index

        fig = go.Figure()

        # Green Lines
        fig.add_trace(go.Scatter(
            x=up_indices,
            y=df.loc[up_indices, "price"],
            mode='lines',
            name='Price Up',
            line=dict(color='green', width=2)
        ))

        # Red Lines
        fig.add_trace(go.Scatter(
            x=down_indices,
            y=df.loc[down_indices, "price"],
            mode='lines',
            name='Price Down',
            line=dict(color='red', width=2)
        ))

        fig.update_layout(
            title=f"{coin_name} Price Movement (Last 24 Hours)",
            xaxis_title="Time",
            yaxis_title="Price (USD)",
            template="plotly_dark"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("Unable to load data.")

# ----------------------
# Main Function
# ----------------------
def main():
    if 'authenticated' not in st.session_state:
        show_login()
    else:
        render_dashboard()

if __name__ == "__main__":
    main()
