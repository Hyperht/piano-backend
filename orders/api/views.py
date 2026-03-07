from rest_framework import viewsets, generics, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError

from products.models import Product
from marketing.models import Coupon
from orders.models import Cart, CartItem
from orders.api.serializers import (
    CartSerializer, CartItemSerializer, 
    OrderListSerializer, OrderDetailSerializer, CheckoutSerializer
)
from orders.selectors.cart import get_user_cart, get_user_cart_items
from orders.selectors.orders import (
    get_user_orders_list, 
    get_user_order_detail,
    get_recent_orders,
    get_all_orders_with_customer
)
from orders.services.order_service import OrderService
from orders.models import Order
from django.utils import timezone
from datetime import timedelta
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination
from tracking.services.tracking_service import TrackingService
import logging
import pandas as pd
from io import BytesIO
from django.http import FileResponse
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

logger = logging.getLogger(__name__)

class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return get_user_cart(self.request.user)

    def list(self, request, *args, **kwargs):
        try:
            cart = self.get_queryset().get()
            serializer = self.get_serializer(cart)
            return Response(serializer.data)
        except Cart.DoesNotExist:
            return Response({
                'items': [], 
                'cart_subtotal': '0.00', 
                'coupon_discount_amount': '0.00', 
                'total_price': '0.00', 
                'coupon': None
            }, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        from orders.services.cart_service import CartService
        
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        
        try:
            updated_cart = CartService.add_item_to_cart(
                user=request.user, 
                product_id=product_id, 
                quantity=quantity, 
                request=request
            )
            serializer = self.get_serializer(updated_cart)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Failed to add item: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

class ApplyCouponView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CartSerializer
    
    def get_object(self):
        try:
            return get_user_cart(self.request.user).get()
        except Cart.DoesNotExist:
            cart, _ = Cart.objects.get_or_create(user=self.request.user)
            return cart

    def put(self, request, *args, **kwargs):
        cart = self.get_object() 
        coupon_code = request.data.get('coupon_code', '').strip()
        
        if not coupon_code:
            return Response({"detail": "Coupon removed."}, status=status.HTTP_200_OK)

        from marketing.services.coupon_service import CouponService
        from rest_framework.exceptions import ValidationError
        
        try:
            cart_subtotal = cart.get_cart_total()
            coupon_result = CouponService.validate_and_calculate_discount(coupon_code, cart_subtotal, request.user)
            
            # Since cart model doesn't store the coupon directly, we just validate it here
            # and let the frontend know the discount amount they'd get.
            return Response({
                "detail": "Coupon applied successfully.",
                "discount_amount": str(coupon_result['discount_amount'])
            }, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            raise ValidationError({'coupon_code': str(e)})

class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return get_user_cart_items(self.request.user)
    
    def perform_create(self, serializer):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        serializer.save(cart=cart)

class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.action == 'retrieve':
            return get_user_order_detail(self.request.user)
        return get_user_orders_list(self.request.user)

    def get_serializer_class(self):
        if self.action == 'list':
            return OrderListSerializer
        if self.action == 'retrieve':
            return OrderDetailSerializer
        return super().get_serializer_class()

class CheckoutView(generics.CreateAPIView):
    serializer_class = CheckoutSerializer
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        try:
            TrackingService.track_checkout(request)
        except Exception as te:
            logger.warning(f"Checkout tracking failed for order: {te}")
        order_serializer = OrderDetailSerializer(order, context={'request': request})
        return Response(order_serializer.data, status=status.HTTP_201_CREATED)

class UpdateOrderStatusAPIView(APIView):
    """
    API endpoint for admins to change an order's status.
    """
    permission_classes = [IsAdminUser]

    def patch(self, request, order_id):
        new_status = request.data.get('status')
        if not new_status:
            return Response({'error': 'Status is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            updated_order = OrderService.transition_order_status(order, new_status)
            return Response({'message': 'Order status updated.', 'status': updated_order.status}, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f"Failed to update status: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class RecentOrdersAPIView(APIView):
    """
    Returns last 5 recent orders for Dashboard summary.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        range_filter = request.query_params.get("range", "30d")
        end_date = timezone.now()

        if range_filter == "7d":
            start_date = end_date - timedelta(days=7)
        elif range_filter == "30d":
            start_date = end_date - timedelta(days=30)
        elif range_filter == "3m":
            start_date = end_date - timedelta(days=90)
        elif range_filter == "1y":
            start_date = end_date - timedelta(days=365)
        else:
            start_date = None

        orders = get_recent_orders(limit=5, start_date=start_date, end_date=end_date)
        
        data = []
        for order in orders:
            user_full_name = 'Unknown'
            if order.user:
                if order.user.first_name or order.user.last_name:
                    user_full_name = f"{order.user.first_name} {order.user.last_name}".strip()
                elif getattr(order.user, 'name', None):
                    user_full_name = order.user.name.strip()
                elif order.user.username:
                    user_full_name = order.user.username.strip()
                else:
                    user_full_name = order.user.email.strip()

            data.append({
                "id": order.id,
                "status": order.status,
                "total_amount": order.total_amount,
                "cart_subtotal": order.cart_subtotal,
                "created_at": order.created_at,
                "user": {
                    "full_name": user_full_name
                }
            })
        return Response(data)

class AllOrdersAPIView(APIView):
    """
    Returns full CRM dataset for all orders (See All).
    Supports pagination, search by order ID, and filter by status.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        range_filter = request.query_params.get("range", "30d")
        search = request.query_params.get("search", "").strip()
        status_filter = request.query_params.get("status", "").strip()
        
        end_date = timezone.now()

        if range_filter == "7d":
            start_date = end_date - timedelta(days=7)
        elif range_filter == "30d":
            start_date = end_date - timedelta(days=30)
        elif range_filter == "3m":
            start_date = end_date - timedelta(days=90)
        elif range_filter == "1y":
            start_date = end_date - timedelta(days=365)
        else:
            start_date = None

        queryset = get_all_orders_with_customer(start_date=start_date, end_date=end_date)
        
        if search:
            if search.isdigit():
                queryset = queryset.filter(id=int(search))
                
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        paginator = StandardResultsSetPagination()
        paginated_queryset = paginator.paginate_queryset(queryset, request, view=self)
        
        return paginator.get_paginated_response(list(paginated_queryset))

class ExportOrdersAPIView(APIView):
    """
    Exports the current filtered orders list as Excel or PDF.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        export_type = request.query_params.get("export_type", "excel")
        range_filter = request.query_params.get("range", "30d")
        search = request.query_params.get("search", "").strip()
        status_filter = request.query_params.get("status", "").strip()
        
        end_date = timezone.now()
        start_date = None

        if range_filter == "7d":
            start_date = end_date - timedelta(days=7)
        elif range_filter == "30d":
            start_date = end_date - timedelta(days=30)
        elif range_filter == "3m":
            start_date = end_date - timedelta(days=90)
        elif range_filter == "1y":
            start_date = end_date - timedelta(days=365)

        queryset = get_all_orders_with_customer(start_date=start_date, end_date=end_date)
        
        if search:
            if search.isdigit():
                queryset = queryset.filter(id=int(search))
                
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        data = list(queryset)

        if export_type == 'pdf':
            output = BytesIO()
            doc = SimpleDocTemplate(output, pagesize=landscape(letter))
            elements = []
            styles = getSampleStyleSheet()
            
            elements.append(Paragraph("Orders Export Report", styles['Title']))
            elements.append(Spacer(1, 12))
            
            table_data = [['ID', 'Status', 'Total', 'Customer', 'Phone', 'City']]
            for o in data:
                customer_name = o.get('full_name', '').strip() or o.get('user__email', '') or 'Unknown User'
                table_data.append([
                    str(o.get('id', '')),
                    o.get('status', '') or '',
                    f"${o.get('total_amount', 0):.2f}",
                    customer_name,
                    o.get('phone1', '') or '',
                    o.get('city', '') or ''
                ])
                
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(table)
            doc.build(elements)
            
            output.seek(0)
            return FileResponse(
                output,
                as_attachment=True,
                filename=f'orders_export_{end_date.date()}.pdf',
                content_type='application/pdf'
            )
        else:
            df_orders = pd.DataFrame([{
                'Order ID': o.get('id', ''),
                'Status': o.get('status', '') or '',
                'Total Amount': float(o.get('total_amount', 0) or 0),
                'Customer Name': o.get('full_name', '').strip() or o.get('user__email', '') or 'Unknown User',
                'Phone': o.get('phone1', ''),
                'City': o.get('city', ''),
                'Address': o.get('street_address', ''),
            } for o in data])
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_orders.to_excel(writer, index=False, sheet_name='Orders')
                
            output.seek(0)
            return FileResponse(
                output,
                as_attachment=True,
                filename=f'orders_export_{end_date.date()}.xlsx',
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
