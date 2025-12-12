"""
Stock Screener - Now with LIVE market data
"""
import yfinance as yf

class StockScreener:
    def __init__(self):
        self.name = "Stock Screener"
    
    def get_live_data(self, ticker):
        """Fetch LIVE market cap, volume, sector from Yahoo Finance"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="1d")
            
            if not hist.empty:
                return {
                    'market_cap': info.get('marketCap', 0),
                    'volume': int(hist.iloc[-1]['Volume']),
                    'sector': info.get('sector', 'Unknown'),
                    'company_name': info.get('longName', ticker)
                }
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
        return None
    
    def screen_for_index_addition(self, ticker=None, market_cap=None, volume=None, sector='Technology'):
        """
        Screen stocks - can use LIVE data if only ticker provided
        
        Usage:
          - LIVE: screen_for_index_addition(ticker='AAPL')
          - MANUAL: screen_for_index_addition(market_cap=15000000000, volume=1000000, sector='Technology')
        """
        if ticker and market_cap is None:
            # Fetch LIVE data
            live_data = self.get_live_data(ticker)
            if live_data:
                market_cap = live_data['market_cap']
                volume = live_data['volume']
                sector = live_data['sector']
                company_name = live_data['company_name']
            else:
                return {'error': f'Could not fetch live data for {ticker}'}
        else:
            company_name = ticker if ticker else 'Unknown'
        
        if not all([market_cap, volume]):
            return {'error': 'Please provide either ticker OR (market_cap and volume)'}
        
        score = 0
        reasons = []
        
        # Market cap criterion (S&P 500 threshold $14.5B)
        if market_cap >= 14500000000:
            score += 40
            reasons.append(f"✓ Market cap ${market_cap/1e9:.1f}B meets S&P 500 threshold")
        elif market_cap >= 8000000000:
            score += 25
            reasons.append(f"⚠ Market cap ${market_cap/1e9:.1f}B approaching threshold")
        else:
            reasons.append(f"✗ Market cap ${market_cap/1e9:.1f}B below threshold")
        
        # Liquidity criterion
        if volume >= 1000000:
            score += 30
            reasons.append(f"✓ High volume {volume:,} (excellent liquidity)")
        elif volume >= 500000:
            score += 15
            reasons.append(f"⚠ Moderate volume {volume:,}")
        else:
            reasons.append(f"✗ Low volume {volume:,}")
        
        # Sector bonus
        if sector in ['Technology', 'Healthcare', 'Financial Services', 'Consumer Cyclical']:
            score += 10
            reasons.append(f"✓ High-growth sector ({sector})")
        
        # Generate recommendation
        if score >= 70:
            recommendation = 'STRONG_CANDIDATE'
        elif score >= 50:
            recommendation = 'POTENTIAL_CANDIDATE'
        else:
            recommendation = 'UNLIKELY'
        
        return {
            'ticker': ticker if ticker else 'N/A',
            'company_name': company_name,
            'recommendation': recommendation,
            'score': score,
            'reasons': reasons,
            'market_cap': market_cap,
            'market_cap_billions': round(market_cap / 1e9, 2),
            'daily_volume': volume,
            'sector': sector,
            'data_source': 'Yahoo Finance LIVE' if ticker else 'User Input'
        }
