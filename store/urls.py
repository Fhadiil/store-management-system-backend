from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StoreViewSet, ProductViewSet, SaleViewSet, UserViewSet, dashboard_stats, create_sale, SalesReportAPI, InventoryReportAPI, ExportSalesReport
from .views import MyTokenObtainPairView, MyTokenRefreshView

router = DefaultRouter()
router.register(r'stores', StoreViewSet)
router.register(r'products', ProductViewSet)
router.register(r'sales', SaleViewSet)
router.register(r'users', UserViewSet)


urlpatterns = [
    path('api/', include(router.urls)),
    path('api/dashboard/', dashboard_stats, name='dashboard_stats'),
    path('api/sale/', create_sale, name='create_sale'),
    path('token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', MyTokenRefreshView.as_view(), name='token_refresh'),
    path('api/reports/sales/', SalesReportAPI.as_view(), name='sales_report'),
    path('api/reports/sales/export/', ExportSalesReport.as_view(), name='export_sales_report'),
    path('api/reports/inventory/', InventoryReportAPI.as_view(), name='inventory_report'),
]
