# SYSTEM DOCUMENTATION
> Piano Project — Django Modular Monolith + DDD + Vue Admin Panel  
> Last Updated: 2026-02-21

---

## 1. Architecture Overview

### Pattern: Modular Monolith with DDD Boundaries

The system is a **Modular Monolith** — a single Django process with clearly separated domains. Each Django app represents one bounded context. Domains communicate only through the **Event System** or explicit service calls — never via direct cross-domain ORM queries.

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Layer                             │
│  Vue.js Admin Panel (piano-frontend/src/modules/admin)      │
│  Customer Storefront (piano-frontend/src/modules/shop)      │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP / REST API (DRF)
┌─────────────────────▼───────────────────────────────────────┐
│                   dashboard/  (API Gateway Layer)           │
│   viewsets/ — thin controllers, IsAdminUser, throttled      │
└─────────────────────┬───────────────────────────────────────┘
                      │ imports from
┌─────────┬───────────┼──────────┬──────────┬────────────────┐
│products │  orders   │analytics │   crm    │  marketing     │
│services │  services │ services │ services │   services     │
│selectors│ selectors │ selectors│          │                │
│  models │   models  │          │   models │    models      │
└─────────┴───────────┴──────────┴──────────┴────────────────┘
                      │ events emitted to
┌─────────────────────▼───────────────────────────────────────┐
│             core/events/  (Event Bus)                       │
│   dispatcher.py — synchronous emit/register                 │
│   events.py — OrderCreatedEvent, ProductViewedEvent, etc.   │
└─────────────────────────────────────────────────────────────┘
```

### Layers

| Layer | Location | Rule |
|-------|----------|------|
| **Models** | `<app>/models.py` | Schema only. No business logic. |
| **Services** | `<app>/services/` | All writes and business logic. Events emitted here. |
| **Selectors** | `<app>/selectors/` | Read-only optimized DB queries. No writes. |
| **Views/Viewsets** | `dashboard/viewsets/` | Thin controllers. Delegate to services/selectors. No ORM. |
| **Serializers** | `dashboard/serializers/__init__.py` | Validation + representation. No logic. |
| **Events** | `core/events/` | Cross-domain communication. |

---

## 2. App Responsibility Map

### `products/`
- **Models**: `Product`, `Category`, `Subcategory`, `Color`, `Room`, `Style`, `ProductImage`
- **Create/Update/Delete** → `products/services/`
- **Read queries** → `products/selectors/`
- **Admin API** → `dashboard/viewsets/catalog.py` (`ProductViewSet`, `CategoryViewSet`, etc.)
- **Frontend Components**: `ProductDetail.vue`, `ProductGrid.vue`, `ProductListPage.vue`, `ProductSlider.vue`, `Home.vue`, `CategorySlider.vue`, `RoomSlider.vue`, `StyleSlider.vue`
- **Translation**: `products/translation.py` (django-modeltranslation, EN/AR)

### `orders/`
- **Models**: `Order`, `OrderItem`, `Cart`, `CartItem`
- **Order placement, status transitions** → `orders/services/`
- **Read queries** → `orders/selectors/`
- **Admin API** → `dashboard/viewsets/orders.py` (`OrderViewSet`)
- **Frontend Components**: `CartPage.vue`, `CartSidebar.vue`, `CheckoutPage.vue`, `Orders.vue`, `paymentPage.vue`

### `analytics/`
- **No models** (reads from other domains)
- **Aggregation logic** → `analytics/services/aggregation_service.py` (`AggregationService`)
- **Admin API** → `analytics/api/`
- **Frontend Dashboard**: `Dashboard.vue` (admin panel)

### `dashboard/`
- **No models** (API gateway only)
- **All admin CRUD API** → `dashboard/viewsets/`
- **All admin serializers** → `dashboard/serializers/__init__.py`
- **URL routing** → `dashboard/urls.py`
- **PDF/Excel export** → `dashboard/exports/`
- **Import** → `dashboard/imports/`

### `crm/`
- **Models**: `ContactMessage`, `CustomerProfile`
- **Handler**: `crm/handlers.py` (reacts to `OrderCreatedEvent`)
- **Frontend Components**: `contactus.vue`, `ProfilePage.vue`

### `marketing/`
- **Models**: `Coupon`
- **Coupon apply logic** → `marketing/services/`
- **Admin API** → `marketing/api/` (Top Coupons)
- **Frontend Components**: `PromoBanner.vue`, `PromoGrid.vue`

### `inventory/`
- **Models**: `StockMovement`
- **Stock deduction on order** → `inventory/services/`
- **Admin read** → `dashboard/viewsets/inventory.py`
- **Handler**: `inventory/handlers.py` (reacts to `OrderCreatedEvent`)

### `tracking/`
- **Models**: `ProductViewEvent`, `AddToCartEvent`, `WishlistEvent`, `CheckoutEvent`
- **View tracking** → `tracking/services/`
- **Command**: `clear_seed_data.py` (clears test data)

### `users/`
- **Models**: `CustomUser`, `Address`, `Favorite`, `HeroSlide`, `PromoGridCategory`, `PromoBanner`
- **Auth, addresses, profile** → `users/views.py`
- **Frontend Components**: `LoginPage.vue`, `SignUp.vue`, `ProfilePage.vue`, `AddressesPage.vue`, `AddressList.vue`, `FavPage.vue`

### `vendors/`
- **Models**: `Vendor`
- **Admin API** → `dashboard/viewsets/vendors.py`

### `core/`
- **Event bus** → `core/events/dispatcher.py`
- **Event definitions** → `core/events/events.py`
- **Base classes** → `core/events/base.py`

---

## 3. CRUD Operations Map

| Entity | Create | Update | Delete | Admin API Endpoint |
|--------|--------|--------|--------|--------------------|
| Product | `products/services/` | `products/services/` | `products/services/` | `/dashboard/products/` |
| Category | `products/services/category.py` | viewset default | viewset default | `/dashboard/categories/` |
| Subcategory | viewset default | viewset default | viewset default | `/dashboard/subcategories/` |
| Color | viewset default | viewset default | viewset default | `/dashboard/colors/` |
| Room | viewset default | viewset default | viewset default | `/dashboard/rooms/` |
| Style | viewset default | viewset default | viewset default | `/dashboard/styles/` |
| Order | `orders/services/` | `dashboard/viewsets/orders.py` (status only) | N/A | `/dashboard/orders/` |
| User | `users/views.py` (register) | `users/views.py` | `users/views.py` | `/dashboard/users/` |
| Vendor | viewset default | viewset default | viewset default | `/dashboard/vendors/` |
| Coupon | viewset default | viewset default | viewset default | `/dashboard/coupons/` |
| Promo Banner | viewset default | viewset default | viewset default | `/dashboard/banners/` |
| Hero Slide | viewset default | viewset default | viewset default | `/dashboard/hero-slides/` |
| StockMovement | `inventory/services/` | N/A (read-only) | N/A | `/dashboard/stock-movements/` |

---

## 4. Analytics & Dashboard Logic

All dashboard data is served from **real DB queries**. No fake/hardcoded values exist.

### KPI Cards (served by `/dashboard/analytics/`)

| Metric | Query Location | Notes |
|--------|----------------|-------|
| `total_revenue` | `analytics/selectors/sales.py::get_revenue_metrics()` | Excludes CANCELLED orders |
| `total_orders` | `analytics/selectors/sales.py::get_orders_metrics()` | Count per time window |
| `total_users` | `analytics/selectors/sales.py::get_total_users()` | `CustomUser.objects.count()` |
| `total_products` | `analytics/selectors/sales.py::get_total_products()` | `Product.objects.count()` |

### Charts

| Chart | Endpoint | Query Location |
|-------|----------|----------------|
| Revenue over time | `/dashboard/revenue-chart/?period=30` | `analytics/selectors/sales.py::get_revenue_chart()` |
| Orders over time | `/dashboard/orders-chart/?period=30` | `analytics/selectors/sales.py::get_orders_chart()` |
| Sales by category | `analytics/` response `by_category` key | `analytics/selectors/aggregations.py::get_sales_by_category()` |
| Sales by region | `analytics/` response `by_region` key | `analytics/selectors/aggregations.py::get_sales_by_region()` |
| Order status | `analytics/` response `orders_metrics.by_status` | `analytics/selectors/aggregations.py::get_orders_metrics()` |

### Funnel
- **Served by**: `analytics/` response `funnel_metrics` key
- **Query**: `analytics/selectors/aggregations.py::get_funnel_counts()`
- **Four stages**: Views (`ProductViewEvent`) → Cart adds (`AddToCartEvent`) → Checkouts (`CheckoutEvent`) → Orders (`Order`)
- **Gap analysis**: `analytics/services/aggregation_service.py::_calculate_gap_analysis()` — calculates drop-off ratios and generates warnings

### Top Products
- **KPIs**: `analytics/selectors/sales.py::get_top_selling()`
- **Filterable by category**: `/dashboard/top-products/?category=Furniture`
- **Logic**: `analytics/services/dashboard.py::DashboardService.get_top_selling_products()`

### Stock Needed
- **Query**: `analytics/selectors/sales.py::get_low_stock_products(threshold=3, limit=10)`
- **Shows**: Products below stock threshold, sorted by quantity ascending

### Most Wishlisted
- **Query**: `analytics/selectors/sales.py::get_most_wishlisted()`
- **Counts**: `Product.objects.annotate(wishlist_count=Count('favorite'))`

### Most Watched (Trending)
- **Query**: `analytics/selectors/sales.py::get_most_watched()`
- **Counts**: `Product.views` field (incremented via tracking middleware/service)

---

## 5. Event Flow Map

```
OrderCreatedEvent  (emitted from orders/services/ on successful order placement)
    ├── inventory/handlers.py  → deduct stock from Product.quantity
    └── crm/handlers.py        → update CustomerProfile total_spent

ProductViewedEvent  (emitted from tracking/services/ on product page load)
    └── tracking service       → creates ProductViewEvent record

StockLowEvent  (emitted from inventory/services/ when stock < low_stock_threshold)
    └── inventory/handlers.py  → logs alert (future: email/notification)

OrderStatusChangedEvent  (emitted from orders/services/ on status update)
    └── (reserved for future notification system)
```

**Event bus**: `core/events/dispatcher.py`  
**Handlers are registered in**: each app's `handlers.py`, called during `apps.py::AppConfig.ready()`

---

## 6. Where To Modify Each Feature

| Task | Location |
|------|----------|
| Change order placement logic | `orders/services/` |
| Change stock deduction amount | `inventory/handlers.py` |
| Modify revenue formula (what counts as revenue) | `analytics/selectors/sales.py::get_revenue_metrics()` |
| Add a new dashboard KPI card | `analytics/services/aggregation_service.py::get_dashboard_summary()` + `analytics/services/dashboard.py::get_aggregated_analytics()` |
| Change funnel calculation | `analytics/selectors/aggregations.py::get_funnel_counts()` |
| Change top products logic | `analytics/selectors/sales.py::get_top_selling()` |
| Change low stock threshold | `analytics/selectors/sales.py::get_low_stock_products(threshold=N)` |
| Modify coupon discount logic | `marketing/strategies/` |
| Modify CRM customer tracking | `crm/services/` + `crm/handlers.py` |
| Modify CRUD validation (admin panel) | `dashboard/serializers/__init__.py` |
| Modify product import/export | `dashboard/imports/` and `dashboard/exports/` |
| Modify PDF report | `dashboard/exports/` |
| Add a new admin CRUD view | `dashboard/viewsets/` (new viewset) + `dashboard/serializers/__init__.py` (new serializer) + `dashboard/urls.py` |
| Add a new tracked event | `core/events/events.py` (new event class) + handler in relevant app + register in `apps.py::ready()` |
| Change authentication backend | `users/backends.py` |
| Change social auth adapter | `users/adapters.py` |

---

## 7. Project Structure (Current)

```
piano-backend/
├── core/
│   └── events/
│       ├── base.py          # BaseEvent dataclass
│       ├── dispatcher.py    # emit() / register()
│       └── events.py        # OrderCreatedEvent, ProductViewedEvent, etc.
├── products/
│   ├── models.py
│   ├── services/            # create_product, update_product, create_category
│   ├── selectors/           # product queries
│   ├── events/              # product-specific events
│   └── api/
├── orders/
│   ├── models.py            # Order, OrderItem, Cart, CartItem
│   ├── services/            # place_order, update_order_status
│   └── selectors/
├── inventory/
│   ├── models.py            # StockMovement
│   ├── services/            # deduct_stock, log_movement
│   └── handlers.py          # reacts to OrderCreatedEvent
├── analytics/
│   ├── services/
│   │   ├── aggregation_service.py   # AggregationService (main)
│   │   ├── dashboard.py             # DashboardService (legacy, still used)
│   │   ├── export_service.py
│   │   └── funnel_service.py
│   └── selectors/
│       ├── aggregations.py          # funnel, category, region, traffic source
│       └── sales.py                 # revenue, orders, top selling, charts
├── crm/
│   ├── models.py
│   ├── services/
│   └── handlers.py          # reacts to OrderCreatedEvent
├── marketing/
│   ├── models.py            # Coupon
│   ├── services/
│   ├── strategies/          # discount calculation strategies
│   └── handlers.py
├── tracking/
│   ├── models.py            # ProductViewEvent, AddToCartEvent, etc.
│   ├── services/
│   └── management/commands/
│       ├── seed_analytics.py   # PERFORMANCE-TESTING ONLY
│       └── clear_seed_data.py  # clears seed_analytics records
├── users/
│   ├── models.py            # CustomUser, Address, Favorite, HeroSlide, PromoBanner
│   ├── serializers.py
│   ├── views.py             # customer-facing auth/profile/cart
│   ├── backends.py          # email-based login
│   └── management/commands/
│       └── seed_colors.py   # canonical color palette utility
├── vendors/
│   └── models.py            # Vendor
├── dashboard/
│   ├── serializers/
│   │   └── __init__.py      # ALL admin serializers (single source of truth)
│   ├── viewsets/
│   │   ├── catalog.py       # Product, Category, Color, Room, Style, PromoBanner
│   │   ├── orders.py        # Order
│   │   ├── users.py         # User
│   │   ├── vendors.py       # Vendor
│   │   ├── inventory.py     # StockMovement (read-only)
│   │   ├── marketing.py     # Coupon, HeroSlide, PromoGridCategory
│   │   ├── sales.py         # Cart, CartItem, Favorite (read-only)
│   │   └── tracking.py      # ProductViewEvent (read-only)
│   ├── analytics/           # analytics viewsets (funnel, top products, etc.)
│   ├── exports/             # PDF and Excel export handlers
│   ├── imports/             # product import handlers
│   └── urls.py
└── piano/
    └── settings.py          # env-based config (DEBUG, DB, JWT, CORS, logging)
```

---

## 8. Key Design Decisions

### Authentication
- JWT (`rest_framework_simplejwt`) with 1-day tokens stored in `localStorage`
- Token key: `access_token` (used consistently across admin panel)
- Auth backend: `users/backends.py` — email-based login (not username)
- Social login: Google and Facebook via `django-allauth`

### Database
- **SQLite** in development, production-ready with `CONN_MAX_AGE=600`
- All major models have `db_index=True` on high-cardinality FK/filter fields
- Composite indexes on `Order(status, created_at)`, `Order(user, status)`, etc.

### Caching
- Redis when `REDIS_URL` env var is set; falls back to `LocMemCache` in development

### Multi-language
- `django-modeltranslation` for EN/AR on products (`name`, `description`)
- Locale: `Africa/Cairo` timezone

### Pagination
- DRF default: `PageNumberPagination`, `PAGE_SIZE = 50`

### Throttling
- Anon: 100/hour | User: 1000/hour

### Vendor / Multi-vendor
- `OrderItem.vendor` captures which vendor fulfilled each line item
- `commission_amount` stored per `OrderItem`
- Analytics selectors accept an optional `vendor` filter for scoped reporting
