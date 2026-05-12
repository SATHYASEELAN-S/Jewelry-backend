from django.contrib import admin

 
from apps.products.models import Category, Product, ProductVariant, ProductImage

class ProductImageInline(admin.TabularInline):  # shows images inside product page
    model = ProductImage
    extra = 3  # shows 3 empty image upload slots

class ProductVariantInline(admin.TabularInline):  # shows variants inside product page
    model = ProductVariant
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline, ProductVariantInline]
    prepopulated_fields = {'slug': ('name',)}  # auto-fills slug from name
    list_display  = ['name', 'category', 'gender', 'price', 'is_available']
    list_filter   = ['category', 'gender', 'is_available']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}