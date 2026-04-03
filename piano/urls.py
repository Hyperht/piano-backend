# piano/urls.py

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from marketing.api.views import HeroSlideViewSet, PromoGridCategoryViewSet

# هذا السطر ليس ضروريًا إذا استخدمنا دالة static()، ولكن لا ضرر من بقائه
from django.views.static import serve as static_serve

# Backward compatibility router for legacy endpoints that clients (or older frontend builds) might still call
legacy_router = DefaultRouter()
legacy_router.register(r'hero-slides', HeroSlideViewSet, basename='legacy-hero-slides')
legacy_router.register(r'promo-grid-categories', PromoGridCategoryViewSet, basename='legacy-promo-grid-categories')

# 1. المسارات الأساسية للـ API ولوحة التحكم
urlpatterns = [
    # Renamed to avoid partial collection by catch-all
    path('django-admin/', admin.site.urls),
    # Friendly index for the auth root (shows links to login/registration)
    path('auth/', TemplateView.as_view(template_name='auth_index.html'), name='auth-home'),
    path('api/dashboard/', include('dashboard.urls')),
    path('api/', include('products.api.urls')),
    path('api/', include('orders.api.urls')),
    path('api/marketing/', include('marketing.api.urls')),
    path('api/', include('crm.api.urls')),
    path('api/tracking/', include('tracking.urls')),
    path('api/analytics/', include('analytics.api.urls')),
    path('api/inventory/', include('inventory.api.urls')),
    path('api/', include('users.urls')),
    path('api/', include(legacy_router.urls)),
    path('auth/', include('dj_rest_auth.urls')),
    path('auth/registration/', include('dj_rest_auth.registration.urls')),
    path('accounts/', include('allauth.urls')),
]

# 2. إضافة مسارات خدمة ملفات الميديا (هذا هو التعديل الأهم)
# يجب أن يأتي هذا الجزء *قبل* مسار اصطياد الكل
if settings.DEBUG:
    # Provide a friendly index for the media root (so GET /media/ doesn't show the static.serve 404)
    urlpatterns += [
        path('media/', TemplateView.as_view(template_name='media_index.html'), name='media-home'),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

from django.shortcuts import redirect

# 3. مسار اصطياد الكل لخدمة الواجهة الأمامية يأتي في النهاية
urlpatterns += [
    # Auto-redirect for images missing the media prefix (handles Screenshot...png 404s)
    re_path(r'^(?P<path>.*\.(?:png|jpg|jpeg|gif|webp|svg))$', lambda request, path: redirect(f'/media/{path}')),

    # Updated regex to allow 'admin' to pass through to frontend
    # Only 'django-admin' is now reserved for backend admin
    re_path(r'^(?!django-admin|api|auth|accounts|media).*$', TemplateView.as_view(template_name='index.html'), name='home'),
]
# ملاحظة: أضفت 'media' إلى القائمة المستبعدة كإجراء احترازي إضافي.