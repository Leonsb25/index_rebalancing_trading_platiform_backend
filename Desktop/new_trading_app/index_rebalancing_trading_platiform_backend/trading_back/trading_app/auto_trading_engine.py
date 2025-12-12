"""
Automated Trading Engine with Risk Management
"""
import yfinance as yf
from decimal import Decimal
from datetime import datetime, timedelta
import random
from .models import AutoTradingBot, BotTrade, User, Holding, Transaction
from .ml_models.pivot import PivotStrategy
from .ml_models.nextday_prediction import NextDayPredictor
from .ml_models.stock_screener import StockScreener
from .ml_models.index_rebalancing import IndexRebalancingStrategy


class AutoTradingEngine:
    """
    Automated Trading Engine with Risk-Based Portfolio Management
    """
    
    # Risk configurations
    RISK_CONFIG = {
        'LOW': {
            'max_position_size': 0.10,  # 10% of capital per trade
            'max_portfolio_exposure': 0.40,  # 40% of capital in market
            'stop_loss': 0.05,  # 5% stop loss
            'take_profit': 0.08,  # 8% take profit
            'min_confidence': 70,  # Minimum confidence score
            'stocks': ['AAPL', 'MSFT', 'JNJ', 'PG', 'KO'],  # Blue chips
            'expected_monthly_return': 2.5,
        },
        'MEDIUM': {
            'max_position_size': 0.15,  # 15% per trade
            'max_portfolio_exposure': 0.60,  # 60% in market
            'stop_loss': 0.08,  # 8% stop loss
            'take_profit': 0.12,  # 12% take profit
            'min_confidence': 60,
            'stocks': ['AAPL', 'GOOGL', 'NVDA', 'TSLA', 'AMD', 'META', 'NFLX'],
            'expected_monthly_return': 5.0,
        },
        'HIGH': {
            'max_position_size': 0.20,  # 20% per trade
            'max_portfolio_exposure': 0.80,  # 80% in market
            'stop_loss': 0.12,  # 12% stop loss
            'take_profit': 0.20,  # 20% take profit
            'min_confidence': 50,
            'stocks': ['NVDA', 'TSLA', 'AMD', 'COIN', 'PLTR', 'SOFI', 'RIOT'],
            'expected_monthly_return': 10.0,
        }
    }
    
    DURATION_MULTIPLIER = {
        'SHORT': 1,    # 1-7 days
        'MEDIUM': 2,   # 1-4 weeks
        'LONG': 3,     # 1-3 months
    }
    
    def __init__(self, bot):
        self.bot = bot
        self.config = self.RISK_CONFIG[bot.risk_level]
        self.strategies = {
            'pivot': PivotStrategy() if bot.use_pivot else None,
            'prediction': NextDayPredictor() if bot.use_prediction else None,
            'screener': StockScreener() if bot.use_screener else None,
            'index': IndexRebalancingStrategy() if bot.use_index_rebalancing else None,
        }
    
    def get_live_price(self, ticker):
        """Fetch live price"""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1d")
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
        except:
            pass
        return None
    
    def analyze_stock(self, ticker):
        """
        Analyze stock using all enabled strategies
        Returns combined signal with confidence
        """
        signals = []
        
        # Pivot Strategy
        if self.strategies['pivot']:
            result = self.strategies['pivot'].predict(ticker=ticker)
            if 'error' not in result:
                score = self._signal_to_score(result['signal'])
                signals.append(('Pivot', score, result))
        
        # Next-Day Prediction
        if self.strategies['prediction']:
            result = self.strategies['prediction'].predict(ticker=ticker)
            if 'error' not in result:
                score = result['confidence'] if result['prediction'] == 'UP' else -result['confidence']
                signals.append(('Prediction', score, result))
        
        # Calculate combined signal
        if signals:
            avg_score = sum(s[1] for s in signals) / len(signals)
            confidence = abs(avg_score)
            action = 'BUY' if avg_score > self.config['min_confidence'] else 'HOLD'
            
            return {
                'action': action,
                'confidence': confidence,
                'signals': signals,
                'ticker': ticker
            }
        
        return None
    
    def _signal_to_score(self, signal):
        """Convert signal to numerical score"""
        scores = {
            'STRONG_BUY': 90,
            'BUY': 70,
            'HOLD_BULLISH': 50,
            'HOLD_BEARISH': -50,
            'SELL': -70,
            'STRONG_SELL': -90
        }
        return scores.get(signal, 0)
    
    def execute_buy(self, ticker, analysis):
        """Execute buy order"""
        try:
            price = self.get_live_price(ticker)
            if not price:
                return None
            
            price = Decimal(str(round(price, 2)))
            
            # Calculate position size based on risk
            max_investment = self.bot.current_capital * Decimal(str(self.config['max_position_size']))
            quantity = int(max_investment / price)
            
            if quantity == 0:
                return None
            
            total_cost = price * quantity
            
            # Check if we have enough capital
            if total_cost > self.bot.current_capital:
                return None
            
            # Create holding for user
            holding, created = Holding.objects.get_or_create(
                user=self.bot.user,
                stock=ticker,
                defaults={
                    'quantity': quantity,
                    'buying_price': price,
                    'current_price': price
                }
            )
            
            if not created:
                # Update existing holding
                total_quantity = holding.quantity + quantity
                total_cost_existing = (holding.buying_price * holding.quantity) + (price * quantity)
                holding.buying_price = total_cost_existing / total_quantity
                holding.quantity = total_quantity
                holding.current_price = price
                holding.save()
            
            # Update user balance
            self.bot.user.balance -= total_cost
            self.bot.user.save()
            
            # Update bot capital
            self.bot.current_capital -= total_cost
            self.bot.total_trades += 1
            self.bot.last_trade_at = datetime.now()
            self.bot.save()
            
            # Create transaction
            Transaction.objects.create(
                user=self.bot.user,
                transaction_type='buy',
                debit=total_cost,
                credit=Decimal('0.00'),
                description=f"[BOT] Bought {quantity} shares of {ticker} @ ${price}",
                balance_after=self.bot.user.balance
            )
            
            # Create bot trade record
            bot_trade = BotTrade.objects.create(
                bot=self.bot,
                stock=ticker,
                action='BUY',
                quantity=quantity,
                price=price,
                total_value=total_cost,
                strategy_used=', '.join([s[0] for s in analysis['signals']]),
                confidence_score=Decimal(str(round(analysis['confidence'], 2)))
            )
            
            return bot_trade
            
        except Exception as e:
            print(f"Error executing buy for {ticker}: {e}")
            return None
    
    def execute_sell(self, holding, reason='Stop Loss/Take Profit'):
        """Execute sell order"""
        try:
            price = self.get_live_price(holding.stock)
            if not price:
                return None
            
            price = Decimal(str(round(price, 2)))
            revenue = price * holding.quantity
            profit_loss = revenue - (holding.buying_price * holding.quantity)
            
            # Update user balance
            self.bot.user.balance += revenue
            self.bot.user.save()
            
            # Update bot
            self.bot.current_capital += revenue
            self.bot.total_profit_loss += profit_loss
            self.bot.total_trades += 1
            self.bot.last_trade_at = datetime.now()
            
            if profit_loss > 0:
                self.bot.winning_trades += 1
            else:
                self.bot.losing_trades += 1
            
            self.bot.save()
            
            # Create transaction
            Transaction.objects.create(
                user=self.bot.user,
                transaction_type='sell',
                debit=Decimal('0.00'),
                credit=revenue,
                description=f"[BOT] Sold {holding.quantity} shares of {holding.stock} @ ${price} ({reason})",
                balance_after=self.bot.user.balance
            )
            
            # Create bot trade record
            bot_trade = BotTrade.objects.create(
                bot=self.bot,
                stock=holding.stock,
                action='SELL',
                quantity=holding.quantity,
                price=price,
                total_value=revenue,
                strategy_used=reason,
                profit_loss=profit_loss
            )
            
            # Delete holding
            holding.delete()
            
            return bot_trade
            
        except Exception as e:
            print(f"Error executing sell for {holding.stock}: {e}")
            return None
    
    def check_stop_loss_take_profit(self):
        """Check existing positions for stop loss or take profit"""
        holdings = Holding.objects.filter(user=self.bot.user)
        
        for holding in holdings:
            # Update current price
            current_price = self.get_live_price(holding.stock)
            if current_price:
                holding.current_price = Decimal(str(round(current_price, 2)))
                holding.save()
                
                profit_pct = holding.profit_loss_percentage / 100
                
                # Check stop loss
                if profit_pct <= -self.config['stop_loss']:
                    self.execute_sell(holding, f"Stop Loss Triggered ({profit_pct:.1%})")
                
                # Check take profit
                elif profit_pct >= self.config['take_profit']:
                    self.execute_sell(holding, f"Take Profit Triggered ({profit_pct:.1%})")
    
    def run_trading_cycle(self):
        """Execute one trading cycle"""
        if self.bot.status != 'ACTIVE':
            return {'status': 'Bot is not active'}
        
        results = {
            'analyzed': 0,
            'bought': 0,
            'sold': 0,
            'signals': []
        }
        
        # Check existing positions first
        self.check_stop_loss_take_profit()
        
        # Analyze stocks in watchlist
        for ticker in self.config['stocks']:
            analysis = self.analyze_stock(ticker)
            
            if analysis:
                results['analyzed'] += 1
                results['signals'].append(analysis)
                
                # Execute trades based on signals
                if analysis['action'] == 'BUY' and analysis['confidence'] >= self.config['min_confidence']:
                    trade = self.execute_buy(ticker, analysis)
                    if trade:
                        results['bought'] += 1
        
        return results
