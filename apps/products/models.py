from uuid import uuid4

from django.db import models


class Category(models.Model):
    public_id        = models.UUIDField(default=uuid4, editable=False, unique=True)
    name        = models.CharField(max_length=100)
    slug        = models.SlugField(unique=True)
    image       = models.ImageField(upload_to='categories/', blank=True)
    description = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

class Product(models.Model):
    GENDER_CHOICES = [
        ('male',   'Male'),
        ('female', 'Female'),
        ('unisex', 'Unisex'),
    ]
    
    category     = models.ForeignKey(Category, on_delete=models.RESTRICT, related_name='products')
    name         = models.CharField(max_length=200)
    slug         = models.SlugField(unique=True)
    description  = models.TextField()
    price        = models.DecimalField(max_digits=10, decimal_places=2)
    gender       = models.CharField(max_length=10, choices=GENDER_CHOICES, default='female')   
    is_available = models.BooleanField(default=True)
    is_featured  = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
class ProductVariant(models.Model):
    public_id        = models.UUIDField(default=uuid4, editable=False, unique=True)
    product          = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size             = models.CharField(max_length=20, blank=True) 
    stock            = models.PositiveIntegerField(default=0)
    extra_price      = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.product.name} - {self.stock}"
    
    @property
    def is_in_stock(self):
        return self.stock>0
    
class ProductImage(models.Model):
    public_id        = models.UUIDField(default=uuid4, editable=False, unique=True)
    product    = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image      = models.ImageField(upload_to='products/')
    alt_text   = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"Image for {self.product.name}"