import random
import os
from faker import Faker
from django.core.files import File
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

def get_images_for_category(cat_name):
    """Returns list of image file paths for a category"""
    folder = image_map.get(cat_name)
    if not folder or not os.path.exists(folder):
        return []
    return [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
    ]

categories = list(Category.objects.all())

genders     = ['male', 'female', 'unisex']
ring_sizes  = ['5', '6', '7', '8', '9', '10']
chain_sizes = ['16 inch', '18 inch', '20 inch', '22 inch']
ear_sizes   = ['small', 'medium', 'large']
brac_sizes  = ['small', 'medium', 'large', 'XL']

size_map = {
    'Rings':     ring_sizes,
    'Necklaces': chain_sizes,
    'Earrings':  ear_sizes,
    'Bracelets': brac_sizes,
}

product_names = {
    'Rings':     ['Gold Plated Band Ring', 'Rose Gold Twisted Ring', 'Silver Plated Floral Ring', 'Gold Plated Stone Ring', 'Rose Gold Heart Ring', 'Gold Plated Crown Ring'],
    'Necklaces': ['Gold Plated Pendant Necklace', 'Rose Gold Chain Necklace', 'Silver Plated Choker', 'Gold Plated Heart Necklace', 'Rose Gold Layered Necklace'],
    'Earrings':  ['Gold Plated Hoop Earrings', 'Rose Gold Drop Earrings', 'Silver Plated Stud Earrings', 'Gold Plated Chandelier Earrings', 'Rose Gold Ear Cuff'],
    'Bracelets': ['Gold Plated Bangle Bracelet', 'Rose Gold Chain Bracelet', 'Silver Plated Charm Bracelet', 'Gold Plated Tennis Bracelet', 'Rose Gold Cuff Bracelet'],
}

for i in range(100):
    category  = random.choice(categories)
    cat_name  = category.name
    base_name = random.choice(product_names.get(cat_name, ['Gold Plated Jewelry']))
    name      = f"{base_name} {i+1}"
    slug      = f"{name.lower().replace(' ', '-')}"
    gender    = random.choice(genders)
    price     = round(random.uniform(199, 1999), 2)

    if Product.objects.filter(slug=slug).exists():
        slug = f"{slug}-{random.randint(100, 999)}"

    product = Product.objects.create(
        category     = category,
        name         = name,
        slug         = slug,
        description  = fake.paragraph(nb_sentences=3),
        price        = price,
        gender       = gender,
        is_featured  = random.choice([True, False]),
        is_available = True,
    )

    # ── Variants ───────────────────────────────────────────
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

    # ── Images ─────────────────────────────────────────────
    all_images = get_images_for_category(cat_name)

    if all_images:
        num_images = min(random.randint(1, 4), len(all_images))
        selected_imgs = random.sample(all_images, k=num_images)

        for j, img_path in enumerate(selected_imgs):
            with open(img_path, 'rb') as img_file:
                img_name = os.path.basename(img_path)

                ProductImage.objects.create(
                    product=product,
                    image=File(img_file, name=img_name),
                    alt_text=f"{name} view {j+1}",
                    is_primary=(j == 0),
                )

            print(f"  Image {j+1}: {img_name}")

    else:
        print(f"  No images found for {cat_name}")

    print(f"[{i+1}/100] Created: {name}")

print("\n Done! 100 products with variants and images created!")
