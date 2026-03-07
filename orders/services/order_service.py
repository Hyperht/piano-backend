from decimal import Decimal
from django.db import transaction
from orders.models import Cart, Order, OrderItem
from users.models import Address
from core.events.dispatcher import emit
from core.events.events import OrderCreatedEvent, OrderStatusChangedEvent
import logging

logger = logging.getLogger(__name__)


class OrderService:

    @staticmethod
    @transaction.atomic
    def place_order(user, address_data: dict, payment_method: str, coupon_code: str = None) -> Order:
        """
        Service for processing a cart checkout, creating the order,
        items, and calculating commissions. Emits OrderCreatedEvent.
        """
        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            raise ValueError("User does not have an active cart.")

        if not cart.items.exists():
            raise ValueError("Cannot checkout on an empty cart.")

        cart_subtotal = cart.get_cart_total()

        # Create shipping address
        shipping_address = Address.objects.create(user=user, **address_data)

        # Calculate Shipping Cost
        shipping_cost = shipping_address.area.shipping_cost if shipping_address.area else Decimal('0.00')

        # Validate and Apply Coupon
        from marketing.services.coupon_service import CouponService
        try:
            coupon_result = CouponService.validate_and_calculate_discount(coupon_code, cart_subtotal, user)
            coupon = coupon_result['coupon']
            coupon_discount_amount = coupon_result['discount_amount']
        except Exception as e:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(str(e))

        final_total = (cart_subtotal + shipping_cost) - coupon_discount_amount
        if final_total < Decimal('0.00'):
            final_total = Decimal('0.00')

        cart_subtotal = cart_subtotal.quantize(Decimal('0.01'))
        shipping_cost = shipping_cost.quantize(Decimal('0.01'))
        coupon_discount_amount = coupon_discount_amount.quantize(Decimal('0.01'))
        final_total = final_total.quantize(Decimal('0.01'))

        # Snapshot region from shipping address
        region_snapshot = None
        if shipping_address.area and shipping_address.area.governorate:
            region_snapshot = shipping_address.area.governorate.name

        order = Order.objects.create(
            user=user,
            shipping_address=shipping_address,
            cart_subtotal=cart_subtotal,
            shipping_cost=shipping_cost,
            coupon_discount=coupon_discount_amount,
            coupon_code_used=coupon.code if coupon else None,
            total_amount=final_total,
            final_total=final_total,
            payment_method=payment_method,
            region_snapshot=region_snapshot,
            status='NEW',
        )

        # Record Coupon Usage
        if coupon:
            CouponService.record_usage(coupon, user, order, coupon_discount_amount)

        order_items = []
        for cart_item in cart.items.select_related('product', 'product__vendor').all():
            product = cart_item.product
            price_snapshot = product.get_current_price()
            subtotal = price_snapshot * cart_item.quantity

            vendor = product.vendor
            commission_rate = vendor.commission_rate if vendor else Decimal('0.00')
            commission_amount = (subtotal * commission_rate / Decimal(100)).quantize(Decimal('0.01'))

            if not vendor:
                from vendors.models import Vendor
                vendor = Vendor.objects.first()
                if not vendor:
                    vendor = Vendor.objects.create(name='System Vendor', commission_rate=0.00)

            order_items.append(
                OrderItem(
                    order=order,
                    product=product,
                    vendor=vendor,
                    quantity=cart_item.quantity,
                    price_snapshot=price_snapshot,
                    subtotal=subtotal,
                    commission_amount=commission_amount
                )
            )

        OrderItem.objects.bulk_create(order_items)

        cart.delete()

        # Trigger internal event synchronously
        emit(OrderCreatedEvent(order_id=order.id))
        logger.info(f"Emitted OrderCreatedEvent for Order ID: {order.id}")

        return order

    @staticmethod
    @transaction.atomic
    def create_admin_order(validated_data: dict, items_data: list) -> Order:
        """
        Creates an order manually from the admin dashboard (bypasses cart).
        Handles totals and commission calculation.
        """
        from orders.models import OrderItem
        from vendors.models import Vendor

        order = Order.objects.create(**validated_data)
        total = Decimal('0.00')

        order_items = []
        for item_data in items_data:
            product = item_data['product']
            quantity = item_data['quantity']
            
            price = product.get_current_price()
            subtotal = (price * quantity).quantize(Decimal('0.01'))
            
            vendor = product.vendor
            commission_rate = vendor.commission_rate if vendor else Decimal('0.00')
            commission_amount = (subtotal * commission_rate / Decimal('100.00')).quantize(Decimal('0.01'))
            
            if not vendor:
                vendor = Vendor.objects.first()
                if not vendor:
                    vendor = Vendor.objects.create(name='System Vendor', commission_rate=0.00)

            order_items.append(
                OrderItem(
                    order=order,
                    product=product,
                    vendor=vendor,
                    quantity=quantity,
                    price_snapshot=price,
                    subtotal=subtotal,
                    commission_amount=commission_amount
                )
            )
            total += subtotal

        if order_items:
            OrderItem.objects.bulk_create(order_items)

        order.cart_subtotal = total
        order.total_amount = total
        order.final_total = total
        order.save(update_fields=['cart_subtotal', 'total_amount', 'final_total'])

        emit(OrderCreatedEvent(order_id=order.id))
        logger.info(f"Admin manually created Order ID: {order.id}")

        return order

    @staticmethod
    def transition_order_status(order: Order, new_status: str):
        """
        Transitions order status adhering to strict state rules.
        Handles stock re-incrementation upon cancellation.
        """
        from rest_framework.exceptions import ValidationError

        valid_statuses = [
            'NEW', 'PENDING', 'CONFIRMED', 'PROCESSING', 'SHIPPED', 
            'DELIVERED', 'RETURNED', 'CANCELLED'
        ]

        current_status = getattr(order, 'status', 'NEW').upper()
        new_status = new_status.upper()
        
        # If the frontend accidentally sends the same status, just return it
        if new_status == current_status:
            return order

        if new_status not in valid_statuses:
            raise ValidationError(f"Invalid order status: {new_status}")

        order.status = new_status
        order.save(update_fields=['status'])

        # Stock re-incrementation if cancelled
        if new_status == 'CANCELLED':
            for item in order.items.select_related('product').all():
                product = item.product
                if product:
                    product.quantity += item.quantity
                    if product.quantity > 0 and not product.is_active:
                        product.is_active = True
                    product.save(update_fields=['quantity', 'is_active'])
            logger.info(f"Re-incremented stock for cancelled order {order.id}")

        # Fire event using properly defined event class
        emit(OrderStatusChangedEvent(
            order_id=order.id,
            old_status=current_status,
            new_status=new_status
        ))
        logger.info(f"Order {order.id} transitioned from {current_status} to {new_status}")

        return order
