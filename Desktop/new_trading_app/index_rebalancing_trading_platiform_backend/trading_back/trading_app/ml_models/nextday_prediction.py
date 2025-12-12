"""
Next-Day Price Movement Predictor - Now with LIVE data
"""
import yfinance as yf

class NextDayPredictor:
    def __init__(self):
        self.name = "Next Day Predictor"
    
    def get_live_data(self, ticker):
        """Fetch LIVE OHLCV data from Yahoo Finance"""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2d")
            if not hist.empty:
                today = hist.iloc[-1]
                return {
                    'open': float(today['Open']),
                    'high': float(today['High']),
                    'low': float(today['Low']),
                    'close': float(today['Close']),
                    'volume': int(today['Volume'])
                }
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
        return None
    
    def predict(self, ticker=None, open_price=None, high=None, low=None, close=None, volume=None):
        """
        Predict next day - can use LIVE data if only ticker provided
        
        Usage:
          - LIVE: predict(ticker='AAPL')
          - MANUAL: predict(open_price=150, high=152, low=149, close=151, volume=1000000)
        """
        if ticker and open_price is None:
            # Fetch LIVE data
            live_data = self.get_live_data(ticker)
            if live_data:
                open_price = live_data['open']
                high = live_data['high']
                low = live_data['low']
                close = live_data['close']
                volume = live_data['volume']
            else:
                return {'error': f'Could not fetch live data for {ticker}'}
        
        if not all([open_price, high, low, close, volume]):
            return {'error': 'Please provide either ticker OR all OHLCV values'}
        
        price_change = ((close - open_price) / open_price) * 100
        hl_range = ((high - low) / close) * 100
        
        score = 0
        
        # Bullish indicators
        if price_change > 2:
            score += 3
        elif price_change > 0:
            score += 1
        
        # Bearish indicators
        if price_change < -2:
            score -= 3
        elif price_change < 0:
            score -= 1
        
        # Volatility adjustment
        if hl_range > 5:
            score = score * 0.8
        
        # Generate prediction
        if score >= 2:
            prediction = 'UP'
            confidence = min(70 + (score * 5), 90)
        elif score <= -2:
            prediction = 'DOWN'
            confidence = min(70 + (abs(score) * 5), 90)
        else:
            prediction = 'NEUTRAL'
            confidence = 50
        
        return {
            'stock_symbol': ticker if ticker else 'UNKNOWN',
            'prediction': prediction,
            'confidence': round(confidence, 1),
            'price_change_today': round(price_change, 2),
            'volatility': round(hl_range, 2),
            'current_price': round(close, 2),
            'recommendation': f"Expect price to move {prediction} with {confidence:.0f}% confidence",
            'data_source': 'Yahoo Finance LIVE' if ticker else 'User Input'
        }
