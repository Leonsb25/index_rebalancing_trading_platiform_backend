import os
import requests
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import JsonResponse

ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_KEY', 'demo')

@api_view(['GET'])
def get_live_price(request):
    ticker = request.GET.get('ticker', 'ICLN').upper()
    
    url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={ALPHA_VANTAGE_KEY}'
    
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        price = float(data['Global Quote']['05. price'])
        return Response({
            "ticker": ticker,
            "price": price,
            "change": float(data['Global Quote']['09. change']),
            "change_pct": float(data['Global Quote']['10. change percent'].replace('%', '')),
            "source": "Alpha Vantage LIVE"
        })
    except:
        # Demo fallback
        fallback = {"ICLN": 14.25, "ENPH": 98.50, "TAN": 26.80}
        return Response({
            "ticker": ticker,
            "price": fallback.get(ticker, 15.0),
            "change": 0.25,
            "change_pct": 1.8,
            "source": "Demo"
        })
