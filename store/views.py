from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Store, Product, Sale
from .serializers import StoreSerializer, ProductSerializer, SaleSerializer, UserSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth.models import User


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


# Custom sale creation endpoint
@api_view(['POST'])
def create_sale(request):
    barcode = request.data.get('barcode')
    quantity_sold = request.data.get('quantity')
    
    # Find the product by barcode
    try:
        product = Product.objects.get(barcode=barcode)
    except Product.DoesNotExist:
        return Response({'detail': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if there's enough stock
    if product.stock_quantity < quantity_sold:
        return Response({'detail': 'Insufficient stock'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Calculate total price
    total_price = product.price * quantity_sold
    
    # Update product stock
    product.stock_quantity -= quantity_sold
    product.save()
    
    # Record the sale
    sale = Sale.objects.create(
        product=product,
        store=product.store,
        quantity=quantity_sold,
        total_price=total_price
    )
    
    return Response({'detail': 'Sale recorded successfully', 'sale_id': sale.id}, status=status.HTTP_201_CREATED)


# JWT Token Views
class MyTokenObtainPairView(TokenObtainPairView):
    pass

class MyTokenRefreshView(TokenRefreshView):
    pass

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
