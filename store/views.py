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
def create_sale(request):
    """
    Handles the creation of a sale, updates the stock quantity,
    and generates a sale record.
    """
    if request.method == 'POST':
        store_id = request.data.get('store')
        product_id = request.data.get('product')
        quantity = request.data.get('quantity')

        # Validate if store and product exist
        try:
            store = Store.objects.get(id=store_id)
            product = Product.objects.get(id=product_id)
        except (Store.DoesNotExist, Product.DoesNotExist):
            return Response({"error": "Store or product not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check if there's enough stock
        if product.stock_quantity < quantity:
            return Response({"error": "Not enough stock."}, status=status.HTTP_400_BAD_REQUEST)

        # Update the product's stock quantity
        product.stock_quantity -= quantity
        product.save()

        # Create the sale record
        sale = Sale(store=store, product=product, quantity=quantity)
        sale.save()

        # Serialize the sale data and return the response
        serializer = SaleSerializer(sale)
        return Response(serializer.data, status=status.HTTP_201_CREATED)




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
    """
    Returns summary statistics for the dashboard.
    """
    total_products = Product.objects.count()
    total_sales = Sale.objects.count()
    total_revenue = Sale.objects.aggregate(total_revenue=Sum('total_price'))['total_revenue'] or 0
    total_stores = Store.objects.count()

    # Get top-selling products (ordered by quantity sold)
    top_products = Sale.objects.values('product__name').annotate(
        total_sold=Sum('quantity')
    ).order_by('-total_sold')[:5]  # Top 5 bestsellers

    return Response({
        "total_products": total_products,
        "total_sales": total_sales,
        "total_revenue": total_revenue,
        "total_stores": total_stores,
        "top_products": top_products
    }, status=status.HTTP_200_OK)

