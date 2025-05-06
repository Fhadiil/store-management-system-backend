from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .models import Store, Product, Sale
from .serializers import StoreSerializer, ProductSerializer, SaleSerializer, UserSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth.models import User
from django.db.models import Sum
from django.db import transaction


# Add to views.py
from datetime import datetime, timedelta
from django.db.models import Q
from django.db.models import Count, Sum


# Store ViewSet (standard CRUD for stores)
class StoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer


# Product ViewSet (standard CRUD and search for products)
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_queryset(self):
        """
        Optionally filter by 'barcode' or 'name'.
        """
        queryset = Product.objects.all()
        barcode = self.request.query_params.get('barcode', None)
        name = self.request.query_params.get('name', None)

        if barcode:
            queryset = queryset.filter(barcode__icontains=barcode)  # Case-insensitive search for barcode
        if name:
            queryset = queryset.filter(name__icontains=name)  # Case-insensitive search for name

        return queryset

    # Custom create logic for product creation
    def create(self, request, *args, **kwargs):
        data = request.data
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            # Save the product
            product = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Sale ViewSet (standard CRUD for sales)
class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer


@api_view(['POST'])
@transaction.atomic
def create_sale(request):
    try:
        data = request.data
        product = Product.objects.select_for_update().get(id=data['product'])
        
        if product.stock_quantity < data['quantity']:
            return Response(
                {"error": f"Only {product.stock_quantity} items available"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        product.stock_quantity -= data['quantity']
        product.save()
        
        sale = Sale.objects.create(
            store_id=data['store'],
            product=product,
            quantity=data['quantity']
        )
        
        return Response(SaleSerializer(sale).data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)




# JWT Token Views
class MyTokenObtainPairView(TokenObtainPairView):
    pass

class MyTokenRefreshView(TokenRefreshView):
    pass

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


@api_view(['GET'])
def dashboard_stats(request):
    # Get store_id if filtering by store
    store_id = request.query_params.get('store_id')
    
    filters = {}
    if store_id:
        filters['store_id'] = store_id
    
    # Optimize queries with single aggregation
    stats = Sale.objects.filter(**filters).aggregate(
        total_sales=Count('id'),
        total_revenue=Sum('total_price'),
        total_items_sold=Sum('quantity')
    )
    
    # Get low stock alert count
    low_stock_count = Product.objects.filter(
        stock_quantity__lte=10,
        **filters
    ).count()
    
    return Response({
        **stats,
        "low_stock_alert": low_stock_count,
        "total_products": Product.objects.filter(**filters).count(),
        "top_products": Sale.objects.filter(**filters).values(
            'product__name'
        ).annotate(
            total_sold=Sum('quantity')
        ).order_by('-total_sold')[:5]
    })



class SalesReportAPI(APIView):
    def get(self, request):
        # Get query parameters with defaults
        time_range = request.query_params.get('range', 'weekly')
        store_id = request.query_params.get('store_id')
        
        # Calculate date range
        now = datetime.now()
        if time_range == 'daily':
            date_from = now - timedelta(days=1)
        elif time_range == 'monthly':
            date_from = now - timedelta(days=30)
        else:  # weekly
            date_from = now - timedelta(days=7)
        
        # Base queryset
        queryset = Sale.objects.filter(date__gte=date_from)
        
        # Filter by store if specified
        if store_id:
            queryset = queryset.filter(store_id=store_id)
        
        # Generate report data
        report_data = queryset.values(
            'product__name',
            'product__barcode'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('total_price')
        ).order_by('-total_revenue')
        
        return Response(report_data)

class InventoryReportAPI(APIView):
    def get(self, request):
        threshold = int(request.query_params.get('threshold', 10))
        
        low_stock = Product.objects.filter(
            stock_quantity__lte=threshold
        ).values(
            'id', 'name', 'barcode', 'stock_quantity'
        ).order_by('stock_quantity')
        
        return Response(low_stock)
    
    
# In views.py
from django.http import HttpResponse
import csv

class ExportSalesReport(APIView):
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sales_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Product', 'Barcode', 'Quantity Sold', 'Revenue'])
        
        data = SalesReportAPI().get(request).data
        for item in data:
            writer.writerow([
                item['product__name'],
                item['product__barcode'],
                item['total_quantity'],
                item['total_revenue']
            ])
        
        return response