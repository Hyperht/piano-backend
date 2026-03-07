import hashlib
import json
from typing import Dict, Any, List
from django.core.cache import cache

from analytics.selectors.aggregations import (
    get_funnel_counts,
    get_intent_metrics,
    get_traffic_source_breakdown
)

class FunnelService:
    """
    Orchestrates specialized conversion and traffic analytics requests.
    Implements Redis/Database caching for heavy aggregations.
    """
    CACHE_TTL = 60 * 15  # 15 minutes by default
    
    @staticmethod
    def _generate_cache_key(prefix: str, filters: Dict[str, Any]) -> str:
        """
        Generates a deterministic cache key based on query filters.
        """
        # Sort keys to ensure consistent hashing
        filter_str = json.dumps(filters, sort_keys=True, default=str)
        filter_hash = hashlib.md5(filter_str.encode('utf-8')).hexdigest()
        return f"analytics:{prefix}:{filter_hash}"

    @staticmethod
    def get_funnel_data(filters: Dict[str, Any]) -> Dict[str, Any]:
        cache_key = FunnelService._generate_cache_key("funnel", filters)
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            return cached_data
            
        counts = get_funnel_counts(filters)
        
        views = counts.get('views', 0)
        cart = counts.get('adds_to_cart', 0)
        checkout = counts.get('checkouts', 0)
        orders = counts.get('orders', 0)
        
        funnel_data = {
            'counts': counts,
            'conversion_rates': {
                'view_to_cart': (cart / views * 100) if views > 0 else 0,
                'cart_to_checkout': (checkout / cart * 100) if cart > 0 else 0,
                'checkout_to_order': (orders / checkout * 100) if checkout > 0 else 0,
                'overall_conversion': (orders / views * 100) if views > 0 else 0
            }
        }
        
        cache.set(cache_key, funnel_data, FunnelService.CACHE_TTL)
        return funnel_data

    @staticmethod
    def get_intent_data(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        cache_key = FunnelService._generate_cache_key("intent", filters)
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            return cached_data
            
        intent_data = get_intent_metrics(filters)
        cache.set(cache_key, intent_data, FunnelService.CACHE_TTL)
        return intent_data

    @staticmethod
    def get_traffic_source_data(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        cache_key = FunnelService._generate_cache_key("traffic", filters)
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            return cached_data
            
        traffic_data = get_traffic_source_breakdown(filters)
        
        # Calculate conversion rate per traffic source if needed (e.g., orders / views per source)
        # Note: True cross-domain view counts per traffic source requires a separate tracking aggregation 
        # or a grouped selector. For now, we return revenue and order volume per source.
        
        cache.set(cache_key, traffic_data, FunnelService.CACHE_TTL)
        return traffic_data
