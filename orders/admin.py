from django.contrib import admin
from .models import Order, OrderItem, Cart, CartItem

# -----------------------
# Shopping Cart Admin
# -----------------------
class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('product',)
    fields = ('product', 'quantity',)

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__email')
    inlines = [CartItemInline]
    readonly_fields = ('user', 'created_at', 'updated_at')

# -----------------------
# Order Admin
# -----------------------
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    # fields need to match model. OrderItem has price_snapshot, commission_amount etc.
    # users/admin.py had price_at_purchase. 
    # New OrderItem has price_snapshot.
    readonly_fields = ('product', 'quantity', 'price_snapshot', 'subtotal')
    fields = ('product', 'quantity', 'price_snapshot', 'subtotal')
    can_delete = False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total_amount', 'created_at')
    list_filter = ('status',)
    list_editable = ('status',)
    search_fields = ('id', 'user__username')
    inlines = [OrderItemInline]
    readonly_fields = (
        'user', 
        'address', 
        'cart_subtotal', 
        'shipping_cost', 
        'coupon_discount', 
        'total_amount', 
        # 'coupon_code_used', # check if exists in new model
        # 'payment_method', 
        # 'payment_status', 
        # 'transaction_id', 
        'created_at', 
        'updated_at'
    )
    
    # Matching fields from new model
    fieldsets = (
        (None, {
            'fields': ('status', 'user', 'address', 'traffic_source')
        }),
        ('Financials', {
            'fields': ('cart_subtotal', 'shipping_cost', 'coupon_discount', 'total_amount')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
