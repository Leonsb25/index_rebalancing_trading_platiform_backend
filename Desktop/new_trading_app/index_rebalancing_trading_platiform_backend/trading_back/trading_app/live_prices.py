"""
Live Stock Price Fetcher using Yahoo Finance - FREE API
"""
import yfinance as yf
from decimal import Decimal
from datetime import datetime
from rest_framework.decorators import api_view
from rest_framework.response import Response


def get_stock_data(ticker):
    """Fetch comprehensive stock data from Yahoo Finance"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="5d")
        
        if hist.empty:
            return None
            
        current = hist.iloc[-1]
        prev_day = hist.iloc[-2] if len(hist) > 1 else current
        
        return {
            'ticker': ticker.upper(),
            'current_price': float(current['Close']),
            'open': float(current['Open']),
            'high': float(current['High']),
            'low': float(current['Low']),
            'volume': int(current['Volume']),
            'prev_close': float(prev_day['Close']),
            'prev_high': float(prev_day['High']),
            'prev_low': float(prev_day['Low']),
            'prev_volume': int(prev_day['Volume']),
            'change': float(current['Close'] - prev_day['Close']),
            'change_percent': float(((current['Close'] - prev_day['Close']) / prev_day['Close']) * 100),
            'timestamp': datetime.now().isoformat(),
            'market_cap': info.get('marketCap', 'N/A'),
            'company_name': info.get('longName', ticker),
            'sector': info.get('sector', 'N/A'),
            'source': 'Yahoo Finance LIVE'
        }
    except Exception as e:
        print(f"Error fetching {ticker}: {str(e)}")
        return None


@api_view(['GET'])
def get_live_price(request):
    """API: /api/live-price/?ticker=AAPL"""
    ticker = request.GET.get('ticker', 'AAPL').upper()
    data = get_stock_data(ticker)
    
    if data:
        return Response(data)
    return Response({'error': f'Could not fetch data for {ticker}'}, status=400)


@api_view(['POST'])
def get_multiple_prices(request):
    """API: POST /api/live-prices/ Body: {"tickers": ["AAPL", "GOOGL"]}"""
    tickers = request.data.get('tickers', [])
    
    if not tickers:
        return Response({'error': 'No tickers provided'}, status=400)
    
    results = {}
    for ticker in tickers:
        data = get_stock_data(ticker)
        if data:
            results[ticker] = data
    
    return Response({
        'count': len(results),
        'stocks': results,
        'timestamp': datetime.now().isoformat()
    })
