import uuid
from typing import Optional
from django.http import HttpRequest
from users.models import CustomUser
from products.models import Product
from vendors.models import Vendor
from tracking.models import (
    ProductViewEvent,
    AddToCartEvent,
    WishlistEvent,
    CheckoutEvent
)
from core.events.dispatcher import emit
from core.events.events import ProductViewedEvent

class TrackingService:
    @staticmethod
    def _get_or_create_session_id(request: HttpRequest) -> str:
        if not request.session.session_key:
            request.session.create()
        return request.session.session_key or str(uuid.uuid4())

    @staticmethod
    def resolve_traffic_source(request: HttpRequest) -> str:
        """
        Determines traffic source from request parameters or headers.
        Priority: UTM Source -> Campaign -> Referrer -> Direct
        """
        utm_source = request.GET.get('utm_source')
        if utm_source:
            return f"utm_{utm_source}"
            
        campaign = request.GET.get('campaign')
        if campaign:
            return f"campaign_{campaign}"
            
        referrer = request.META.get('HTTP_REFERER')
        if referrer:
            if 'google.com' in referrer:
                return 'organic_google'
            elif 'facebook.com' in referrer or 'instagram.com' in referrer:
                return 'social_meta'
            return 'referral'
            
        return 'direct'

    @staticmethod
    def track_product_view(request: HttpRequest, product: Product) -> ProductViewEvent:
        user = request.user if request.user.is_authenticated else None
        session_id = TrackingService._get_or_create_session_id(request)
        
        event = ProductViewEvent.objects.create(
            user=user,
            product=product,
            vendor=product.vendor,
            session_id=session_id,
            traffic_source=TrackingService.resolve_traffic_source(request)
        )
        
        emit(ProductViewedEvent(
            product_id=product.id,
            user_id=user.id if user else None,
            session_key=session_id
        ))
        
        return event

    @staticmethod
    def track_add_to_cart(request: HttpRequest, product: Product) -> AddToCartEvent:
        user = request.user if request.user.is_authenticated else None
        
        return AddToCartEvent.objects.create(
            user=user,
            product=product,
            vendor=product.vendor,
            session_id=TrackingService._get_or_create_session_id(request),
            traffic_source=TrackingService.resolve_traffic_source(request)
        )

    @staticmethod
    def track_wishlist(request: HttpRequest, product: Product) -> WishlistEvent:
        if not request.user.is_authenticated:
            raise ValueError("User must be authenticated to track wishlist event")
            
        return WishlistEvent.objects.create(
            user=request.user,
            product=product,
            vendor=product.vendor,
            traffic_source=TrackingService.resolve_traffic_source(request)
        )

    @staticmethod
    def track_checkout(request: HttpRequest) -> CheckoutEvent:
        user = request.user if request.user.is_authenticated else None
        
        return CheckoutEvent.objects.create(
            user=user,
            session_id=TrackingService._get_or_create_session_id(request),
            traffic_source=TrackingService.resolve_traffic_source(request)
        )
