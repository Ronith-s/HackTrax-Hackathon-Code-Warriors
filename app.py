from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import csv
from functools import lru_cache

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Enable CORS for frontend

# ✅ Load ingredient classifications from CSV
def load_ingredient_database():
    ingredient_db = {}
    try:
        with open("ingredients.csv", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                ingredient_db[row["ingredient"].lower()] = row["category"].lower()
    except FileNotFoundError:
        print("⚠️ Warning: 'ingredients.csv' not found. Using empty database.")
    return ingredient_db

INGREDIENT_DATABASE = load_ingredient_database()

# ✅ Fetch product details from OpenFoodFacts API
@lru_cache(maxsize=50)
def fetch_product_by_name(product_name):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={product_name}&search_simple=1&json=1"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        products = data.get("products", [])
        if products:
            product = products[0]  # Take first result
            barcode = product.get("code")
            return fetch_product_by_barcode(barcode) if barcode else product
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching product: {e}")
    return None

@lru_cache(maxsize=50)
def fetch_product_by_barcode(barcode):
    url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json().get("product", {})
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching barcode data: {e}")
    return None

# ✅ Better Ingredient Matching (Partial Matching)
def find_ingredient_category(ingredient):
    ingredient = ingredient.lower()
    for known_ingredient, category in INGREDIENT_DATABASE.items():
        if known_ingredient in ingredient:  # Partial match
            return category
    return None

# ✅ Calculate Eco-Score (Ingredients + Packaging)
def calculate_eco_score(product):
    """ Calculate eco-score based on structured ingredient data & packaging. """
    score = 50  # Default base score
    harmful_ingredients = []
    good_ingredients = []

    # 🔹 Extract structured ingredients
    ingredients_list = product.get("ingredients", [])
    if not ingredients_list:
        print("⚠️ Warning: No structured ingredients found!")
        return {
            "eco_score": score,
            "good_ingredients": [],
            "harmful_ingredients": []
        }

    print(f"✅ Extracted Ingredients: {[i['text'] for i in ingredients_list if 'text' in i]}")  

    for ingredient_data in ingredients_list:
        ingredient_name = ingredient_data.get("text", "").lower().strip()
        if not ingredient_name:
            continue  # Skip empty ingredients

        category = find_ingredient_category(ingredient_name)

        if category == "harmful":
            harmful_ingredients.append(ingredient_name)
            score -= 15
        elif category == "good":
            good_ingredients.append(ingredient_name)
            score += 10

    # 🔹 Consider Packaging Impact (if available)
    packaging_materials = product.get("packaging", "").lower().split(",")
    if "plastic" in packaging_materials:
        score -= 10  # Deduct points for plastic use
    elif "paper" in packaging_materials:
        score += 5   # Add points for paper-based packaging

    print(f"👍 Good: {good_ingredients}, 🚫 Harmful: {harmful_ingredients}, 📦 Packaging: {packaging_materials}, 🎯 Final Score: {score}")

    return {
        "eco_score": max(0, min(100, score)),  # Keep score within 0-100
        "good_ingredients": good_ingredients,
        "harmful_ingredients": harmful_ingredients
    }

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Eco-Friendly Product Comparer API is running!"})

@app.route("/compare", methods=["POST"])
def compare_products():
    """ Compare multiple products based on eco-score. """
    if request.method != "POST":
        return jsonify({"error": "Method Not Allowed"}), 405

    data = request.get_json()
    if not data or "product_names" not in data or not isinstance(data["product_names"], list):
        return jsonify({"error": "Invalid request format"}), 400

    products = []
    for name in data["product_names"]:
        product_data = fetch_product_by_name(name)
        if product_data:
            eco_data = calculate_eco_score(product_data)
            products.append({
                "name": product_data.get("product_name", "Unknown"),
                "image": product_data.get("image_url", ""),
                "eco_score": eco_data["eco_score"],
                "good_ingredients": eco_data["good_ingredients"],
                "harmful_ingredients": eco_data["harmful_ingredients"]
            })

    # Sort products by eco-score (higher is better)
    products.sort(key=lambda x: x["eco_score"], reverse=True)

    return jsonify({"comparison": products})

# ✅ Debugging: Print available routes
print("Registered Routes:")
for rule in app.url_map.iter_rules():
    print(rule)

if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)
