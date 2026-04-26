import random
from faker import Faker
from apps.products.models import Category, Product, ProductVariant

fake = Faker()

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
        category    = category,
        name        = name,
        slug        = slug,
        description = fake.paragraph(nb_sentences=3),
        price       = price,
        gender      = gender,
        is_featured = random.choice([True, False]),
        is_available= True,
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

print("Done! Created 100 products with variants!")