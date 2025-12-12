"""
Create Sample Trading Data with LIVE Stock Prices from Yahoo Finance
"""
import os
import django
import sys
import yfinance as yf
from decimal import Decimal
from datetime import datetime
import random

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trading_back.settings')
django.setup()

from trading_app.models import User, Transaction, Holding


def get_live_stock_data(ticker):
    """Fetch LIVE price and historical data from Yahoo Finance"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")
        info = stock.info
        
        if hist.empty:
            print(f"⚠️  No data available for {ticker}")
            return None
            
        current = hist.iloc[-1]
        prev_day = hist.iloc[-2] if len(hist) > 1 else current
        
        return {
            'ticker': ticker.upper(),
            'current_price': Decimal(str(round(float(current['Close']), 2))),
            'open': Decimal(str(round(float(current['Open']), 2))),
            'high': Decimal(str(round(float(current['High']), 2))),
            'low': Decimal(str(round(float(current['Low']), 2))),
            'volume': int(current['Volume']),
            'prev_close': Decimal(str(round(float(prev_day['Close']), 2))),
            'prev_high': Decimal(str(round(float(prev_day['High']), 2))),
            'prev_low': Decimal(str(round(float(prev_day['Low']), 2))),
            'market_cap': info.get('marketCap', 0),
            'sector': info.get('sector', 'Technology'),
            'company_name': info.get('longName', ticker)
        }
    except Exception as e:
        print(f"❌ Error fetching {ticker}: {str(e)}")
        return None


def simulate_buying_price(current_price, days_ago=7):
    """Simulate realistic buying price from X days ago"""
    variance = random.uniform(-0.10, 0.05)  # -10% to +5%
    buying_price = current_price * Decimal(1 + variance)
    return Decimal(str(round(buying_price, 2)))


print("="*70)
print("🚀 CREATING LIVE DEMO DATA FOR CLASS PRESENTATION")
print("="*70)

# Create demo user
print("\n🔄 Setting up demo user...")
user, created = User.objects.get_or_create(
    email='trader@demo.com',
    defaults={
        'username': 'demo_trader',
        'name': 'Demo Trader',
        'userid': 'DEMO001',
        'balance': Decimal('100000.00')
    }
)

if created:
    user.set_password('demo123')
    user.save()
    print(f"✅ Created new user: {user.email}")
else:
    print(f"✅ User exists: {user.email}")
    # Clear old data for fresh demo
    user.holdings.all().delete()
    user.transactions.all().delete()
    user.balance = Decimal('100000.00')
    user.save()
    print("🗑️  Cleared old data - fresh start!")

# Stocks to trade with different ML strategies
stocks_to_trade = [
    {'ticker': 'NVDA', 'strategy': 'Index Rebalancing - S&P 500 Addition', 'quantity': 10},
    {'ticker': 'AAPL', 'strategy': 'Pivot Point Strategy', 'quantity': 20},
    {'ticker': 'TSLA', 'strategy': 'Next-Day Predictor', 'quantity': 15},
    {'ticker': 'GOOGL', 'strategy': 'Stock Screener - Index Candidate', 'quantity': 25},
]

print("\n📡 FETCHING LIVE DATA FROM YAHOO FINANCE...")
print("-"*70)

# Create holdings with LIVE prices
for stock_info in stocks_to_trade:
    ticker = stock_info['ticker']
    quantity = stock_info['quantity']
    strategy = stock_info['strategy']
    
    print(f"\n🔍 Fetching {ticker}...", end=" ")
    
    live_data = get_live_stock_data(ticker)
    
    if live_data:
        current_price = live_data['current_price']
        buying_price = simulate_buying_price(current_price, days_ago=7)
        
        print(f"✅ ${current_price}")
        print(f"   📊 Company: {live_data['company_name']}")
        print(f"   📈 Prev Close: ${live_data['prev_close']} | High: ${live_data['prev_high']} | Low: ${live_data['prev_low']}")
        
        # Create holding
        holding = Holding.objects.create(
            user=user,
            stock=ticker,
            quantity=quantity,
            buying_price=buying_price,
            current_price=current_price
        )
        
        # Create buy transaction
        cost = quantity * buying_price
        user.balance -= cost
        user.save()
        
        Transaction.objects.create(
            user=user,
            transaction_type='buy',
            debit=cost,
            credit=Decimal('0.00'),
            description=f"Bought {quantity} shares of {ticker} @ ${buying_price} using {strategy}",
            balance_after=user.balance
        )
        
        profit_loss = holding.profit_loss
        profit_pct = holding.profit_loss_percentage
        status = "🟢 PROFIT" if profit_loss > 0 else "🔴 LOSS"
        
        print(f"   💰 Buy Price: ${buying_price} → Current: ${current_price}")
        print(f"   {status}: ${profit_loss:+,.2f} ({profit_pct:+.2f}%)")
    else:
        print("❌ FAILED")

# Calculate portfolio performance
total_invested = sum(h.total_invested for h in user.holdings.all())
total_current = sum(h.current_value for h in user.holdings.all())
total_profit = total_current - total_invested
profit_pct = (total_profit / total_invested) * 100 if total_invested > 0 else 0

print("\n" + "="*70)
print("📊 LIVE PORTFOLIO SUMMARY (FOR CLASS DEMO)")
print("="*70)
print(f"💰 Cash Balance:    ${user.balance:>12,.2f}")
print(f"💵 Total Invested:  ${total_invested:>12,.2f}")
print(f"📈 Current Value:   ${total_current:>12,.2f}")
print(f"{'🟢' if total_profit >= 0 else '🔴'} Total P/L:      ${total_profit:>12,.2f} ({profit_pct:+.2f}%)")
print(f"📦 Holdings:        {user.holdings.count():>12} stocks")
print(f"🕐 Generated:       {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}")
print("="*70)

# Individual holdings
print("\n📈 INDIVIDUAL HOLDINGS (LIVE DATA):")
print("="*70)
for holding in user.holdings.all():
    pnl = holding.profit_loss
    pnl_pct = holding.profit_loss_percentage
    status_emoji = "🟢" if pnl >= 0 else "🔴"
    
    print(f"\n{status_emoji} {holding.stock:6} | {holding.quantity:3} shares")
    print(f"   Buy:     ${holding.buying_price:>7.2f}")
    print(f"   Current: ${holding.current_price:>7.2f}")
    print(f"   P/L:     ${pnl:>+7.2f} ({pnl_pct:+.2f}%)")
    print(f"   Value:   ${holding.current_value:>7.2f}")

print("\n" + "="*70)
print("✅ LIVE DEMO DATA CREATED SUCCESSFULLY!")
print("="*70)
print("\n🔑 LOGIN CREDENTIALS FOR CLASS:")
print("   📧 Email:    trader@demo.com")
print("   🔒 Password: demo123")
print("\n💡 All prices are LIVE from Yahoo Finance!")
print("   Run this script before class for latest data")
print("="*70)
