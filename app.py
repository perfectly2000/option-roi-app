from flask import Flask, render_template, request
import yfinance as yf
from datetime import datetime, timedelta

app = Flask(__name__)

def get_expiry_dates():
    today = datetime.today()
    return [
        (today + timedelta(days=90)).strftime('%Y-%m-%d'),
        (today + timedelta(days=180)).strftime('%Y-%m-%d'),
        (today + timedelta(days=365)).strftime('%Y-%m-%d')
    ]

def fetch_option_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        price = stock.history(period='1d')['Close'].iloc[-1]
        expiries = stock.options
        target_dates = get_expiry_dates()

        result = []
        for date in target_dates:
            try:
                closest_date = min(expiries, key=lambda x: abs(datetime.strptime(x, "%Y-%m-%d") - datetime.strptime(date, "%Y-%m-%d")))
                options = stock.option_chain(closest_date).puts
                sorted_options = options.sort_values('strike')
                atm_idx = (sorted_options['strike'] - price).abs().idxmin()
                atm_index_pos = sorted_options.index.get_loc(atm_idx)
                comparison_data = []

                indices = range(max(0, atm_index_pos - 5), min(len(sorted_options), atm_index_pos + 6))
                for i in indices:
                    row = sorted_options.iloc[i]
                    strike = row['strike']
                    bid = row['bid']
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
                result.append([])
        return result
    except Exception as e:
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    results = {}
    if request.method == 'POST':
        tickers = request.form['tickers'].splitlines()
        for ticker in tickers:
            ticker = ticker.strip().upper()
            if ticker:
                results[ticker] = fetch_option_data(ticker)
    return render_template('index.html', results=results)

if __name__ == '__main__':
    app.run(debug=True)