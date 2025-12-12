"""
ML Strategy Views with LIVE Data Integration
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import yfinance as yf
from .ml_models.pivot import PivotStrategy
from .ml_models.nextday_prediction import NextDayPredictor
from .ml_models.stock_screener import StockScreener
from .ml_models.index_rebalancing import IndexRebalancingStrategy


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pivot_analysis(request):
    """
    Pivot Point Analysis
    If only 'ticker' provided: fetch LIVE data from Yahoo Finance
    Otherwise: use provided high/low/close values
    """
    try:
        data = request.data
        ticker = data.get('ticker')
        
        strategy = PivotStrategy()
        
        # If ticker provided and no manual data, fetch live
        if ticker and not all([data.get('high'), data.get('low'), data.get('close')]):
            result = strategy.predict(ticker=ticker)
        else:
            # Use manual data
            high = float(data.get('high', 0))
            low = float(data.get('low', 0))
            close = float(data.get('close', 0))
            
            if not all([high, low, close]):
                return Response({
                    'error': 'Please provide either ticker OR (high, low, close) values'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            result = strategy.predict(high=high, low=low, close=close)
        
        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result)
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def next_day_prediction(request):
    """
    Next-Day Price Prediction
    If only 'stock_symbol' provided: fetch LIVE data
    Otherwise: use provided OHLCV data
    """
    try:
        data = request.data
        ticker = data.get('stock_symbol') or data.get('ticker')
        
        predictor = NextDayPredictor()
        
        # If ticker provided and no manual data, fetch live
        if ticker and not data.get('open_price'):
            result = predictor.predict(ticker=ticker)
        else:
            # Use manual data
            open_price = float(data.get('open_price', 0))
            high = float(data.get('high', 0))
            low = float(data.get('low', 0))
            close = float(data.get('close', 0))
            volume = int(data.get('volume', 0))
            
            if not all([open_price, high, low, close, volume]):
                return Response({
                    'error': 'Please provide either ticker OR all OHLCV values'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            result = predictor.predict(
                ticker=ticker,
                open_price=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume
            )
        
        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result)
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def stock_screener(request):
    """
    Stock Screener for Index Addition
    If only 'ticker' provided: fetch LIVE market cap, volume, sector
    Otherwise: use provided values
    """
    try:
        data = request.data
        ticker = data.get('ticker')
        
        screener = StockScreener()
        
        # If ticker provided and no manual data, fetch live
        if ticker and not data.get('market_cap'):
            result = screener.screen_for_index_addition(ticker=ticker)
        else:
            # Use manual data
            market_cap = float(data.get('market_cap', 0))
            volume = int(data.get('volume', 0))
            sector = data.get('sector', 'Technology')
            
            if not all([market_cap, volume]):
                return Response({
                    'error': 'Please provide either ticker OR (market_cap and volume)'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            result = screener.screen_for_index_addition(
                ticker=ticker,
                market_cap=market_cap,
                volume=volume,
                sector=sector
            )
        
        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result)
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def index_rebalancing_analysis(request):
    """
    Index Reconstitution Event Analysis
    Fetches LIVE current price if ticker provided
    """
    try:
        data = request.data
        
        stock_symbol = data.get('stock_symbol')
        event_type = data.get('event_type', 'ADD')
        announcement_date = data.get('announcement_date')
        effective_date = data.get('effective_date')
        current_price = data.get('current_price')
        index_name = data.get('index_name', 'SP500')
        
        # Validate required fields
        if not all([stock_symbol, announcement_date, effective_date]):
            return Response({
                'error': 'Missing required fields: stock_symbol, announcement_date, effective_date'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Fetch live price if not provided
        if not current_price:
            try:
                stock = yf.Ticker(stock_symbol)
                hist = stock.history(period="1d")
                if not hist.empty:
                    current_price = float(hist['Close'].iloc[-1])
                else:
                    return Response({
                        'error': f'Could not fetch current price for {stock_symbol}'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response({
                    'error': f'Could not fetch current price for {stock_symbol}'
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            current_price = float(current_price)
        
        strategy = IndexRebalancingStrategy()
        result = strategy.analyze_event(
            stock_symbol=stock_symbol,
            event_type=event_type,
            announcement_date=announcement_date,
            effective_date=effective_date,
            current_price=current_price,
            index_name=index_name
        )
        
        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result)
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
