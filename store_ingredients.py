import requests
import json

def fetch_product_data(product_name):
    """ Fetch product data from OpenFoodFacts API """
    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={product_name}&search_simple=1&json=1"
    response = requests.get(url)

    if response.status_code != 200:
        print(f"Failed to fetch data for {product_name}")
        return None

    data = response.json().get("products", [])
    if not data:
        print(f"No product found for {product_name}")
        return None

    product = data[0]  # Take first search result
    ingredients = product.get("ingredients_text", "Unknown").split(", ")

    return {
        "name": product.get("product_name", product_name),
        "ingredients": ingredients,
        "image": product.get("image_url", ""),
    }

def save_ingredients(product_names):
    """ Fetch and save ingredients to a JSON file """
    products_data = []

    for name in product_names:
        product_data = fetch_product_data(name)
        if product_data:
            products_data.append(product_data)

    # Save data to JSON file
    with open("ingredients_data.json", "w", encoding="utf-8") as f:
        json.dump(products_data, f, indent=4)

    return products_data  # Return the saved data for confirmation
