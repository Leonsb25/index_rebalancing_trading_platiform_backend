"""
Trading App Views with LIVE Price Integration
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from decimal import Decimal
import yfinance as yf
from .models import User, Transaction, Holding
from .serializers import (
    UserSerializer, TransactionSerializer, HoldingSerializer,
    UserRegistrationSerializer, UserLoginSerializer
)


def get_live_price(ticker):
    """Fetch current live price from Yahoo Finance"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
    except:
        pass
    return None


# Authentication Views
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """User registration"""
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """User login"""
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        user = authenticate(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password']
        )
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data
            })
        return Response({
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """User logout"""
    try:
        request.user.auth_token.delete()
        return Response({'message': 'Successfully logged out'})
    except:
        return Response({'error': 'Logout failed'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile(request):
    """Get user profile"""
    return Response(UserSerializer(request.user).data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """Update user profile"""
    serializer = UserSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Trading Views with LIVE PRICES
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def buy_stock(request):
    """Buy stock at LIVE market price"""
    try:
        stock = request.data.get('stock', '').upper()
        quantity = int(request.data.get('quantity', 0))
        
        if not stock or quantity <= 0:
            return Response({
                'error': 'Invalid stock symbol or quantity'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Fetch LIVE price
        current_price = get_live_price(stock)
        if not current_price:
            return Response({
                'error': f'Could not fetch live price for {stock}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        current_price = Decimal(str(round(current_price, 2)))
        cost = current_price * quantity
        
        user = request.user
        
        # Check balance
        if user.balance < cost:
            return Response({
                'error': f'Insufficient balance. Need ${cost}, have ${user.balance}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update or create holding
        holding, created = Holding.objects.get_or_create(
            user=user,
            stock=stock,
            defaults={
                'quantity': quantity,
                'buying_price': current_price,
                'current_price': current_price
            }
        )
        
        if not created:
            # Update existing holding - calculate new average price
            total_quantity = holding.quantity + quantity
            total_cost = (holding.buying_price * holding.quantity) + (current_price * quantity)
            holding.buying_price = total_cost / total_quantity
            holding.quantity = total_quantity
            holding.current_price = current_price
            holding.save()
        
        # Deduct balance
        user.balance -= cost
        user.save()
        
        # Create transaction
        Transaction.objects.create(
            user=user,
            transaction_type='buy',
            debit=cost,
            credit=Decimal('0.00'),
            description=f"Bought {quantity} shares of {stock} @ ${current_price}",
            balance_after=user.balance
        )
        
        return Response({
            'message': f'Successfully bought {quantity} shares of {stock} at ${current_price}',
            'stock': stock,
            'quantity': quantity,
            'price': float(current_price),
            'total_cost': float(cost),
            'new_balance': float(user.balance)
        })
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sell_stock(request):
    """Sell stock at LIVE market price"""
    try:
        stock = request.data.get('stock', '').upper()
        quantity = int(request.data.get('quantity', 0))
        
        if not stock or quantity <= 0:
            return Response({
                'error': 'Invalid stock symbol or quantity'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        
        # Check if user has holding
        try:
            holding = Holding.objects.get(user=user, stock=stock)
        except Holding.DoesNotExist:
            return Response({
                'error': f'You do not own {stock}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if holding.quantity < quantity:
            return Response({
                'error': f'Insufficient shares. You have {holding.quantity}, trying to sell {quantity}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Fetch LIVE price
        current_price = get_live_price(stock)
        if not current_price:
            return Response({
                'error': f'Could not fetch live price for {stock}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        current_price = Decimal(str(round(current_price, 2)))
        revenue = current_price * quantity
        
        # Update holding
        if holding.quantity == quantity:
            holding.delete()
        else:
            holding.quantity -= quantity
            holding.current_price = current_price
            holding.save()
        
        # Add to balance
        user.balance += revenue
        user.save()
        
        # Create transaction
        Transaction.objects.create(
            user=user,
            transaction_type='sell',
            debit=Decimal('0.00'),
            credit=revenue,
            description=f"Sold {quantity} shares of {stock} @ ${current_price}",
            balance_after=user.balance
        )
        
        return Response({
            'message': f'Successfully sold {quantity} shares of {stock} at ${current_price}',
            'stock': stock,
            'quantity': quantity,
            'price': float(current_price),
            'total_revenue': float(revenue),
            'new_balance': float(user.balance)
        })
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Portfolio Summary
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def portfolio_summary(request):
    """Get portfolio summary with LIVE prices"""
    try:
        user = request.user
        holdings = Holding.objects.filter(user=user)
        
        # Update all holdings with live prices
        for holding in holdings:
            live_price = get_live_price(holding.stock)
            if live_price:
                holding.current_price = Decimal(str(round(live_price, 2)))
                holding.save()
        
        total_invested = sum(h.total_invested for h in holdings)
        total_current = sum(h.current_value for h in holdings)
        total_profit_loss = total_current - total_invested
        profit_loss_pct = (total_profit_loss / total_invested * 100) if total_invested > 0 else 0
        
        return Response({
            'total_balance': float(user.balance),
            'total_invested': float(total_invested),
            'total_current_value': float(total_current),
            'total_profit_loss': float(total_profit_loss),
            'total_profit_loss_percentage': round(profit_loss_pct, 2),
            'holdings_count': holdings.count(),
            'transactions_count': Transaction.objects.filter(user=user).count()
        })
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ViewSets
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user).order_by('-date')
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        transactions = self.get_queryset()[:10]
        serializer = self.get_serializer(transactions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        transactions = self.get_queryset()
        total_debit = sum(t.debit for t in transactions)
        total_credit = sum(t.credit for t in transactions)
        return Response({
            'total_debit': float(total_debit),
            'total_credit': float(total_credit),
            'net': float(total_credit - total_debit)
        })


class HoldingViewSet(viewsets.ModelViewSet):
    serializer_class = HoldingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Holding.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        holdings = self.get_queryset()
        
        # Update with live prices
        for holding in holdings:
            live_price = get_live_price(holding.stock)
            if live_price:
                holding.current_price = Decimal(str(round(live_price, 2)))
                holding.save()
        
        total_value = sum(h.current_value for h in holdings)
        total_invested = sum(h.total_invested for h in holdings)
        
        return Response({
            'total_holdings': holdings.count(),
            'total_value': float(total_value),
            'total_invested': float(total_invested),
            'total_profit_loss': float(total_value - total_invested)
        })
    
    @action(detail=False, methods=['get'])
    def profitable(self, request):
        holdings = [h for h in self.get_queryset() if h.profit_loss > 0]
        serializer = self.get_serializer(holdings, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def losing(self, request):
        holdings = [h for h in self.get_queryset() if h.profit_loss < 0]
        serializer = self.get_serializer(holdings, many=True)
        return Response(serializer.data)
