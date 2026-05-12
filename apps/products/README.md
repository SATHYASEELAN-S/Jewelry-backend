# Products App 📦

This app handles the entire product catalog for the Jewelry e-commerce platform. It includes categories, products, variants, and images with a fully optimized REST API.

---

## 📁 App Structure

```
apps/products/
├── management/
│   └── commands/
│       └── seed.py          # Dummy data seeder
├── migrations/              # Database migrations
├── __init__.py
├── admin.py                 # Django admin configuration
├── apps.py
├── models.py                # Category, Product, ProductVariant, ProductImage
├── serializers.py           # DRF serializers
├── urls.py                  # Product URL routes
└── views.py                 # API views
```

---

## 🗄 Models

### `Category`
| Field | Type | Description |
|---|---|---|
| `name` | CharField | Category name (e.g. Rings, Necklaces) |
| `slug` | SlugField | SEO-friendly unique URL identifier |
| `image` | ImageField | Category banner image |
| `description` | TextField | Category description |
| `created_at` | DateTimeField | Auto timestamp |

### `Product`
| Field | Type | Description |
|---|---|---|
| `category` | ForeignKey | Linked category |
| `name` | CharField | Product name |
| `slug` | SlugField | SEO-friendly unique URL identifier |
| `description` | TextField | Product description |
| `price` | DecimalField | Base price |
| `gender` | CharField | male / female / unisex |
| `is_available` | BooleanField | Show/hide product |
| `is_featured` | BooleanField | Feature on homepage |
| `created_at` | DateTimeField | Auto timestamp |
| `updated_at` | DateTimeField | Auto update timestamp |

### `ProductVariant`
| Field | Type | Description |
|---|---|---|
| `product` | ForeignKey | Linked product |
| `size` | CharField | Size (e.g. 6, 18 inch, small) |
| `stock` | PositiveIntegerField | Available stock |
| `extra_price` | DecimalField | Additional cost over base price |

### `ProductImage`
| Field | Type | Description |
|---|---|---|
| `product` | ForeignKey | Linked product |
| `image` | ImageField | Product image |
| `alt_text` | CharField | Image alt text |
| `is_primary` | BooleanField | Main display image |

### Relationships
```
Category
   └── Product  (many products per category)
          ├── ProductVariant  (many variants per product)
          └── ProductImage    (many images per product)
```

---

## 🌐 API Endpoints

Base URL: `/api/v1/`

| Method | Endpoint | Description |
|---|---|---|
| GET | `/categories/` | List all categories |
| GET | `/products/` | List all products |
| GET | `/products/?gender=female` | Filter by gender |
| GET | `/products/?category=rings` | Filter by category slug |
| GET | `/products/?featured=true` | Featured products only |
| GET | `/products/?page=2` | Pagination |
| GET | `/products/<slug>/` | Single product detail |

### Sample Response — Product List
```json
{
    "count": 110,
    "next": "http://localhost:8000/api/v1/products/?page=2",
    "previous": null,
    "results": [
        {
            "id": 1,
            "name": "Rose Gold Plated Ring",
            "slug": "rose-gold-plated-ring",
            "description": "Beautiful rose gold plated ring for everyday wear.",
            "price": "499.00",
            "gender": "female",
            "is_available": true,
            "is_featured": true,
            "category": {
                "id": 1,
                "name": "Rings",
                "slug": "rings",
                "image": "/media/categories/rings.jpg"
            },
            "variants": [
                {
                    "id": 1,
                    "size": "6",
                    "stock": 10,
                    "extra_price": "0.00"
                }
            ],
            "images": []
        }
    ]
}
```

---

## ⚡ Performance Optimizations

- `select_related('category')` → fetches product + category in a single JOIN query
- `prefetch_related('variants', 'images')` → fetches all variants and images in bulk
- **Result**: Only **4 queries** per request regardless of page size

```
Query 1 → COUNT total products (pagination)
Query 2 → SELECT products + category (INNER JOIN)
Query 3 → SELECT all variants for current page
Query 4 → SELECT all images for current page
```

---

## 📄 Pagination

Configured in `settings.py`:
```python
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10
}
```

Custom pagination allows users to change page size:
```
/api/v1/products/?page=1
/api/v1/products/?page=2&page_size=20   ← max 50
```

---

## 📖 API Documentation

| URL | Description |
|---|---|
| `http://localhost:8000/api/docs/` | ReDoc API documentation |
| `http://localhost:8000/api/schema/` | OpenAPI schema (JSON) |

---

## 🌱 Seed Dummy Data

To populate the database with dummy data:
```bash
python manage.py seed
```

This creates:
- 4 categories (Rings, Necklaces, Earrings, Bracelets)
- 100 products with random names, prices, genders
- 2-4 variants per product with different sizes and stock

---

## 🛠 Admin Configuration

Products are managed via Django Admin with inline support:
- `ProductImageInline` → upload multiple images per product
- `ProductVariantInline` → add multiple variants per product
- Auto slug generation from product name
- Filter by category, gender, availability

Visit: `http://localhost:8000/admin`