from flask import Flask, render_template, Response, request, send_file
import yfinance as yf
import datetime
import os
import asyncio
import json
import pandas as pd

app = Flask(__name__)

def get_5_year_high(stock_symbol):
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=5*365)
    
    try:
        data = yf.download(stock_symbol + ".NS", start=start_date, end=end_date)
        if data.empty:
            raise ValueError("No data found for symbol: " + stock_symbol)
        max_high = round(data['High'].max(), 2)
        max_high_date = data['High'].idxmax()
        return max_high, max_high_date.strftime('%d-%m-%Y')
    except Exception as e:
        return None, str(e)

def get_stock_data(stock_symbol):
    try:
        stock = yf.Ticker(stock_symbol + ".NS")
        ltp = round(stock.history(period="1d")['Close'].iloc[-1], 2)
        data = stock.history(period="1y")
        year_high = round(data['High'].max(), 2)
        five_year_high, high_date = get_5_year_high(stock_symbol)
        trigger_percentage = round(((ltp-five_year_high)/five_year_high)*100, 2)
        return stock_symbol, ltp, year_high, five_year_high, high_date, trigger_percentage
    except Exception as e:
        return stock_symbol, None, None, None, str(e)

async def fetch_stock_data_async(stock_symbol):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: get_stock_data(stock_symbol))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/find_high', methods=['GET', 'POST'])
def find_high():
    stock_symbol = None
    five_year_high = None
    high_date = None
    error_message = None
    ltp = None
    
    if request.method == 'POST':
        stock_symbol = request.form['stock_symbol']
        five_year_high, high_date = get_5_year_high(stock_symbol)
        
        stock = yf.Ticker(stock_symbol + ".NS")
        ltp = round(stock.history(period="1d")['Close'].iloc[-1], 2)
    
    return render_template(
        'find_high.html', stock_symbol=stock_symbol, five_year_high=five_year_high,
        high_date=high_date, error_message=error_message, ltp=ltp
        )

@app.route('/stream_stocks')
def stream_stocks():
    def generate_stock_data():
        stock_symbols = []
        with open('symbols.txt', 'r') as file:
            stock_symbols = file.read().splitlines()
        
        for symbol in stock_symbols:
            stock_data = asyncio.run(fetch_stock_data_async(symbol))
            yield f"data:{json.dumps(stock_data)}\n\n"

    return Response(generate_stock_data(), content_type='text/event-stream')

@app.route('/stock_info')
def stock_info():
    return render_template('stock_info.html')

@app.route('/export_stock_data')
def export_stock_data():
    stock_symbols = []
    with open('symbols.txt', 'r') as file:
        stock_symbols = file.read().splitlines()

    data = []
    for symbol in stock_symbols:
        stock_data = get_stock_data(symbol)
        data.append(stock_data)

    df = pd.DataFrame(data, columns=[
        'Stock Name', 'LTP', '52-Week High', '5-Year High', 'Date of 5-Year High', '(LTP-ATH)/ATH%'
    ])
    
    file_path = 'stock_data.xlsx'
    df.to_excel(file_path, index=False)

    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get('PORT', 8080)))
