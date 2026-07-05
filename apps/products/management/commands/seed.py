import random
import os
from faker import Faker
from django.core.files import File
from django.core.management.base import BaseCommand
from apps.products.models import Category, Product, ProductVariant, ProductImage

fake = Faker()

# ── Image folder path ──────────────────────────────────────
BASE_IMAGE_PATH = r"D:\workspace\backend\jewelry_backend\images"

image_map = {
    'Rings':     os.path.join(BASE_IMAGE_PATH, 'rings'),
    'Necklaces': os.path.join(BASE_IMAGE_PATH, 'necklace'),
    'Earrings':  os.path.join(BASE_IMAGE_PATH, 'Earrings'),
    'Bracelets': os.path.join(BASE_IMAGE_PATH, 'bracelet'),
}

size_map = {
    'Rings':     ['5', '6', '7', '8', '9', '10'],
    'Necklaces': ['16 inch', '18 inch', '20 inch', '22 inch'],
    'Earrings':  ['small', 'medium', 'large'],
    'Bracelets': ['small', 'medium', 'large', 'XL'],
}

product_names = {
    'Rings':     ['Gold Plated Band Ring', 'Rose Gold Twisted Ring', 'Silver Plated Floral Ring', 'Gold Plated Stone Ring', 'Rose Gold Heart Ring', 'Gold Plated Crown Ring'],
    'Necklaces': ['Gold Plated Pendant Necklace', 'Rose Gold Chain Necklace', 'Silver Plated Choker', 'Gold Plated Heart Necklace', 'Rose Gold Layered Necklace'],
    'Earrings':  ['Gold Plated Hoop Earrings', 'Rose Gold Drop Earrings', 'Silver Plated Stud Earrings', 'Gold Plated Chandelier Earrings', 'Rose Gold Ear Cuff'],
    'Bracelets': ['Gold Plated Bangle Bracelet', 'Rose Gold Chain Bracelet', 'Silver Plated Charm Bracelet', 'Gold Plated Tennis Bracelet', 'Rose Gold Cuff Bracelet'],
}


def get_images_for_category(cat_name):
    folder = image_map.get(cat_name)
    if not folder or not os.path.exists(folder):
        return []
    return [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
    ]


class Command(BaseCommand):
    help = 'Seed 100 dummy products with images'

    def handle(self, *args, **kwargs):
        category_data = [
            {'name': 'Rings',     'slug': 'rings'},
            {'name': 'Necklaces', 'slug': 'necklaces'},
            {'name': 'Earrings',  'slug': 'earrings'},
            {'name': 'Bracelets', 'slug': 'bracelets'},
        ]
        for cat in category_data:
            Category.objects.get_or_create(slug=cat['slug'], defaults={'name': cat['name']})

        categories = list(Category.objects.all())
        genders    = ['male', 'female', 'unisex']

        for i in range(100):
            category  = random.choice(categories)
            cat_name  = category.name
            base_name = random.choice(product_names.get(cat_name, ['Gold Plated Jewelry']))
            name      = f"{base_name} {i+1}"
            slug      = name.lower().replace(' ', '-')
            price     = round(random.uniform(199, 1999), 2)

            if Product.objects.filter(slug=slug).exists():
                slug = f"{slug}-{random.randint(100, 999)}"

            product = Product.objects.create(
                category     = category,
                name         = name,
                slug         = slug,
                description  = fake.paragraph(nb_sentences=3),
                price        = price,
                gender       = random.choice(genders),
                is_featured  = random.choice([True, False]),
                is_available = True,
            )

            sizes          = size_map.get(cat_name, ['small', 'medium', 'large'])
            selected_sizes = random.sample(sizes, k=random.randint(2, len(sizes)))
            extra          = 0.00

            for size in selected_sizes:
                ProductVariant.objects.create(
                    product     = product,
                    size        = size,
                    stock       = random.randint(1, 30),
                    extra_price = round(extra, 2),
                )
                extra += random.uniform(25, 100)

            all_images = get_images_for_category(cat_name)
            if all_images:
                num_images    = min(random.randint(1, 4), len(all_images))
                selected_imgs = random.sample(all_images, k=num_images)
                for j, img_path in enumerate(selected_imgs):
                    with open(img_path, 'rb') as img_file:
                        img_name = os.path.basename(img_path)
                        ProductImage.objects.create(
                            product    = product,
                            image      = File(img_file, name=img_name),
                            alt_text   = f"{name} view {j+1}",
                            is_primary = (j == 0),
                        )
                self.stdout.write(f"  {num_images} image(s) added for {name}")
            else:
                self.stdout.write(f"  No images found for {cat_name}")

            self.stdout.write(f"[{i+1}/100] Created: {name}")

        self.stdout.write(self.style.SUCCESS("\nDone! 100 products with variants and images created!"))