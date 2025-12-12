"""
Auto Trading Bot API Views
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from decimal import Decimal
from .models import AutoTradingBot, BotTrade
from .auto_trading_engine import AutoTradingEngine
from .serializers import AutoTradingBotSerializer, BotTradeSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_bot(request):
    """Create a new auto trading bot"""
    try:
        user = request.user
        data = request.data
        
        risk_level = data.get('risk_level', 'MEDIUM')
        duration = data.get('duration', 'MEDIUM')
        initial_capital = Decimal(str(data.get('initial_capital', 10000)))
        
        # Validate capital
        if initial_capital > user.balance:
            return Response({
                'error': f'Insufficient balance. You have ${user.balance}, need ${initial_capital}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate expected return
        config = AutoTradingEngine.RISK_CONFIG[risk_level]
        duration_multiplier = AutoTradingEngine.DURATION_MULTIPLIER[duration]
        expected_return = config['expected_monthly_return'] * duration_multiplier
        
        # Create bot
        bot = AutoTradingBot.objects.create(
            user=user,
            name=data.get('name', f'{risk_level} Risk Bot'),
            risk_level=risk_level,
            duration=duration,
            initial_capital=initial_capital,
            current_capital=initial_capital,
            expected_return=Decimal(str(expected_return)),
            use_pivot=data.get('use_pivot', True),
            use_prediction=data.get('use_prediction', True),
            use_screener=data.get('use_screener', True),
            use_index_rebalancing=data.get('use_index_rebalancing', True),
        )
        
        # Deduct from user balance
        user.balance -= initial_capital
        user.save()
        
        return Response({
            'message': 'Trading bot created successfully',
            'bot': AutoTradingBotSerializer(bot).data,
            'expected_return': f"{expected_return}%",
            'risk_profile': config
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_bots(request):
    """List all user's trading bots"""
    bots = AutoTradingBot.objects.filter(user=request.user)
    return Response(AutoTradingBotSerializer(bots, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_bot(request, bot_id):
    """Get specific bot details"""
    bot = get_object_or_404(AutoTradingBot, id=bot_id, user=request.user)
    return Response(AutoTradingBotSerializer(bot).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_bot(request, bot_id):
    """Start/Resume trading bot"""
    bot = get_object_or_404(AutoTradingBot, id=bot_id, user=request.user)
    bot.status = 'ACTIVE'
    bot.save()
    return Response({'message': f'Bot {bot.name} started'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pause_bot(request, bot_id):
    """Pause trading bot"""
    bot = get_object_or_404(AutoTradingBot, id=bot_id, user=request.user)
    bot.status = 'PAUSED'
    bot.save()
    return Response({'message': f'Bot {bot.name} paused'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def stop_bot(request, bot_id):
    """Stop trading bot and return capital"""
    bot = get_object_or_404(AutoTradingBot, id=bot_id, user=request.user)
    
    # Return remaining capital to user
    bot.user.balance += bot.current_capital
    bot.user.save()
    
    bot.status = 'STOPPED'
    bot.save()
    
    return Response({
        'message': f'Bot {bot.name} stopped',
        'capital_returned': float(bot.current_capital),
        'total_profit_loss': float(bot.total_profit_loss),
        'roi': float(bot.roi_percentage)
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def run_bot_cycle(request, bot_id):
    """Execute one trading cycle manually"""
    bot = get_object_or_404(AutoTradingBot, id=bot_id, user=request.user)
    
    engine = AutoTradingEngine(bot)
    results = engine.run_trading_cycle()
    
    return Response({
        'message': 'Trading cycle completed',
        'results': results,
        'bot_stats': {
            'current_capital': float(bot.current_capital),
            'total_profit_loss': float(bot.total_profit_loss),
            'win_rate': float(bot.win_rate),
            'roi': float(bot.roi_percentage)
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_bot_trades(request, bot_id):
    """Get all trades for a bot"""
    bot = get_object_or_404(AutoTradingBot, id=bot_id, user=request.user)
    trades = BotTrade.objects.filter(bot=bot)
    return Response(BotTradeSerializer(trades, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_risk_profiles(request):
    """Get available risk profiles with expected returns"""
    profiles = []
    
    for risk_level, config in AutoTradingEngine.RISK_CONFIG.items():
        for duration, multiplier in AutoTradingEngine.DURATION_MULTIPLIER.items():
            expected_return = config['expected_monthly_return'] * multiplier
            profiles.append({
                'risk_level': risk_level,
                'duration': duration,
                'expected_return': f"{expected_return}%",
                'max_position_size': f"{config['max_position_size']*100}%",
                'stop_loss': f"{config['stop_loss']*100}%",
                'take_profit': f"{config['take_profit']*100}%",
                'stocks': config['stocks']
            })
    
    return Response(profiles)
