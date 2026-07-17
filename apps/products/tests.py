from rest_framework.test import APITestCase
from django.urls import reverse
from apps.products.models import Category,Product

class TestProductAPI(APITestCase):
    def setUp(self):
        self.category=Category.objects.create(name='rings',slug='rings')
        self.product=Product.objects.create(
            category=self.category,
            name="gold plated ring",
            slug="gold-plated-ring",
            description="gold plated ring for female",
            price=499.00,
            gender="female",
            is_available=True,
            is_featured=True,
        )
        self.product1=Product.objects.create(
            category=self.category,
            name="gold plated ring",
            slug="gold-plated-male-ring",
            description="gold plated ring for male",
            price=599,
            gender="male",
            is_available=False,
            is_featured=True,
        )
        
    def test_product_list_return_200(self):
        url=reverse('product-list')
        response=self.client.get(url) 
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.data['results'][0]['price'],'499.00')
        
            
    def test_product_list_search_by_name(self):
        url=reverse('product-list')
        response=self.client.get(url,{'search':'ring'})
        self.assertEqual(response.data['count'],1)
        
    def test_product_list_search_by_gender(self):
        url=reverse('product-list')
        response=self.client.get(url,{'show_all':'true'})
        self.assertEqual(response.data['count'],2)
    
    def test_product_list_search_by_gender_returns_empty(self):
        url=reverse('product-list')
        response=self.client.get(url,{'gender':'male','is_available':"true"})
        self.assertEqual(response.data['count'],0)
        
        
    
