import pandas as pd
import random
from faker import Faker

fake = Faker()

def generate_products(n=1000):
    products = []
    brands = ["Acme", "Globex", "Initech", "Umbrella", "Stark", "Wayne"]
    colors = ["Black", "White", "Blue", "Red", "Green", "Yellow"]
    sizes = ["XS", "S", "M", "L", "XL", "XXL"]

    for i in range(n):
        brand = random.choice(brands)
        color = random.choice(colors)
        size = random.choice(sizes)
        name = f"{fake.word().capitalize()} {fake.word().capitalize()}"
        price = random.randint(100, 2000)
        sku = f"{brand[:3].upper()}-{color[:3].upper()}-{size}"
        variety = f"{size} / {color}"

        product = {
            "name": name,
            "price": price,
            "sku": sku,
            "variety": variety,
            "brand": brand,
            "color": color,
            "size": size
        }
        products.append(product)
    return products

# Generate products
df = pd.DataFrame(generate_products(1000))

# Save as CSV (attributes will be parsed by your FastAPI code)
df.to_csv("products_test_data.csv", index=False)

print("✅ Generated products_test_data.csv with 1000 rows")
