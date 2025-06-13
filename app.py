from flask import Flask, render_template, request
import yfinance as yf
from datetime import datetime, timedelta
import traceback
import os
import requests

app = Flask(__name__)

def get_expiry_dates():
    today = datetime.today()
    return [
        (today + timedelta(days=98)).strftime('%Y-%m-%d'),
        (today + timedelta(days=189)).strftime('%Y-%m-%d'),
        (today + timedelta(days=370)).strftime('%Y-%m-%d')
    ]

def fetch_option_data(ticker):
    try:
        session = requests.Session()
        session.verify = False  # Temporary fix for SSL issues on Render
        stock = yf.Ticker(ticker, session=session)
        price_data = stock.history(period='1d')
        if price_data.empty:
            print(f"No price data for {ticker}")
            return None
        price = price_data['Close'].iloc[-1]

        expiries = stock.options
        if not expiries:
            print(f"No expirations for {ticker}")
            return None

        target_dates = get_expiry_dates()
        result = []

        for date in target_dates:
            try:
                closest_date = min(
                    expiries,
                    key=lambda x: abs(datetime.strptime(x, "%Y-%m-%d") - datetime.strptime(date, "%Y-%m-%d"))
                )
                options = stock.option_chain(closest_date).puts
                sorted_options = options.dropna(subset=["strike", "bid"]).sort_values("strike")
                if sorted_options.empty:
                    continue

                atm_idx = (sorted_options['strike'] - price).abs().idxmin()
                atm_index_pos = sorted_options.index.get_loc(atm_idx)

                comparison_data = []
                indices = range(max(0, atm_index_pos - 5), min(len(sorted_options), atm_index_pos + 6))

                for i in indices:
                    row = sorted_options.iloc[i]
                    strike = row['strike']
                    bid = row['bid']
                    if bid is None or strike is None:
                        continue
                    roi = (bid / (price * 100)) * 100 if price > 0 else 0
                    comparison_data.append({
                        'expiration': closest_date,
                        'strike': round(strike, 2),
                        'bid': round(bid, 2),
                        'roi': round(roi, 2),
                        'price': round(price, 2)
                    })

                result.append(comparison_data)
            except Exception as e:
                print(f"Error for {ticker} on {date}: {e}")
                traceback.print_exc()
                result.append([])
        return result
    except Exception as e:
        print(f"Major error with ticker {ticker}: {e}")
        traceback.print_exc()
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    results = {}
    if request.method == 'POST':
        tickers = request.form['tickers'].splitlines()
        for ticker in tickers:
            ticker = ticker.strip().upper()
            if ticker:
                data = fetch_option_data(ticker)
                if data:
                    results[ticker] = data
    return render_template('index.html', results=results)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)