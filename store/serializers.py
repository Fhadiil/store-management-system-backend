from rest_framework import serializers
from .models import Store, Product, Sale
from django.contrib.auth.models import User


class SaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields = '__all__'

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = '__all__'
        
class ProductSerializer(serializers.ModelSerializer):
    store = StoreSerializer(read_only=True)  # Ensure store is serialized properly
    store_id = serializers.PrimaryKeyRelatedField(
        queryset=Store.objects.all(), source='store', write_only=True
    )

    class Meta:
        model = Product
        fields = "__all__"



class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email'] 


class SalesReportSerializer(serializers.Serializer):
    product__name = serializers.CharField()
    product__barcode = serializers.CharField()
    total_quantity = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)

class InventoryReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'barcode', 'stock_quantity']