import schedule
import time
import datetime
import yfinance as yf
import json
from pathlib import Path

def get_5_year_high(stock_symbol):
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=5*365)
    data = yf.download(stock_symbol + ".NS", start=start_date, end=end_date)
    if data.empty:
        raise ValueError("No data found for symbol: " + stock_symbol)
    max_high = round(data['High'].max(), 2)
    max_high_date = data['High'].idxmax()
    return max_high, max_high_date.strftime('%d-%m-%Y')

def get_stock_data(stock_symbol):
    try:
        stock = yf.Ticker(stock_symbol + ".NS")
        ltp = round(stock.history(period="1d")['Close'].iloc[-1], 2)
        data = stock.history(period="1y")
        year_high = round(data['High'].max(), 2)
        five_year_high, high_date = get_5_year_high(stock_symbol)
        trigger_percentage = round(((ltp-five_year_high)/five_year_high)*100, 2)
        return {
            "stock_symbol": stock_symbol,
            "ltp": ltp,
            "year_high": year_high,
            "five_year_high": five_year_high,
            "high_date": high_date,
            "trigger_percentage": trigger_percentage
        }
    except Exception as e:
        print(f"Error fetching data for {stock_symbol}: {str(e)}")
        return None

def save_stock_data(stock_symbols):
    results = []
    for symbol in stock_symbols:
        data = get_stock_data(symbol)
        if data:
            results.append(data)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"stock_data_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Data saved to {filename}")

def schedule_stock_data_job(stock_symbols):
    save_stock_data(stock_symbols)

def is_weekday():
    return datetime.datetime.now().weekday() < 5

def is_market_hours():
    now = datetime.datetime.now().time()
    return datetime.time(9, 30) <= now <= datetime.time(15, 30)

if __name__ == "__main__":
    # List of stock symbols to fetch data for
    stock_symbols = ["RELIANCE", "TCS", "HDFCBANK"]  # Add more symbols as needed

    # Schedule the job to run every hour from 9:30 AM to 3:30 PM on weekdays
    for hour in range(9, 16):
        schedule.every().day.at(f"{hour:02d}:30").do(
            schedule_stock_data_job, stock_symbols
        ).tag("stock_data_job")

    while True:
        if is_weekday() and is_market_hours():
            schedule.run_pending()
        time.sleep(60)  # Check every minute
