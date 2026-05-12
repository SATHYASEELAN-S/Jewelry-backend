import random
from faker import Faker
from django.core.management.base import BaseCommand
from apps.products.models import Category, Product, ProductVariant

fake = Faker()

size_map = {
    'Rings': ['5', '6', '7', '8', '9', '10'],
    'Necklaces': ['16 inch', '18 inch', '20 inch', '22 inch'],
    'Earrings': ['small', 'medium', 'large'],
    'Bracelets': ['small', 'medium', 'large', 'XL'],
}

product_names = {
    'Rings': ['Gold Plated Band Ring', 'Rose Gold Twisted Ring', 'Silver Plated Floral Ring', 'Gold Plated Stone Ring', 'Rose Gold Heart Ring'],
    'Necklaces': ['Gold Plated Pendant Necklace', 'Rose Gold Chain Necklace', 'Silver Plated Choker', 'Gold Plated Heart Necklace'],
    'Earrings': ['Gold Plated Hoop Earrings', 'Rose Gold Drop Earrings', 'Silver Plated Stud Earrings', 'Gold Plated Chandelier Earrings'],
    'Bracelets': ['Gold Plated Bangle Bracelet', 'Rose Gold Chain Bracelet', 'Silver Plated Charm Bracelet', 'Gold Plated Tennis Bracelet'],
}

class Command(BaseCommand):
    help = 'Seed 100 dummy products'

    def handle(self, *args, **kwargs):
        categories = list(Category.objects.all())
        genders = ['male', 'female', 'unisex']

        for i in range(100):
            category = random.choice(categories)
            cat_name = category.name
            base_name = random.choice(product_names.get(cat_name, ['Gold Plated Jewelry']))
            name = f"{base_name} {i+1}"
            slug = name.lower().replace(' ', '-')

            if Product.objects.filter(slug=slug).exists():
                slug = f"{slug}-{random.randint(100, 999)}"

            product = Product.objects.create(
                category=category,
                name=name,
                slug=slug,
                description=fake.paragraph(nb_sentences=3),
                price=round(random.uniform(199, 1999), 2),
                gender=random.choice(genders),
                is_featured=random.choice([True, False]),
                is_available=True,
            )

            sizes = size_map.get(cat_name, ['small', 'medium', 'large'])
            selected_sizes = random.sample(sizes, k=random.randint(2, len(sizes)))
            extra = 0.00

            for size in selected_sizes:
                ProductVariant.objects.create(
                    product=product,
                    size=size,
                    stock=random.randint(1, 30),
                    extra_price=round(extra, 2),
                )
                extra += random.uniform(25, 100)

        self.stdout.write(self.style.SUCCESS('Done! Created 100 products with variants!'))