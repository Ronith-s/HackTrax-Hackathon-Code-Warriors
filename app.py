import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS globally

@app.route('/compare', methods=['POST'])
def compare_products():
    try:
        data = request.get_json()
        product_names = data.get('product_names', [])
        if not product_names or len(product_names) != 2:
            return jsonify({'error': 'Please provide exactly two product names.'}), 400

        results = []

        for product_name in product_names:
            search_url = "https://world.openfoodfacts.org/cgi/search.pl"
            params = {
                "search_terms": product_name,
                "search_simple": 1,
                "action": "process",
                "json": 1,
            }
            search_response = requests.get(search_url, params=params)
            search_response.raise_for_status()
            search_data = search_response.json()

            if search_data['count'] == 0:
                results.append({
                    'name': product_name,
                    'error': 'Product not found',
                    'eco_score': 0,
                    'good_ingredients': [],
                    'harmful_ingredients': [],
                })
                continue

            product = search_data['products'][0]
            eco_score = int(product.get('ecoscore_score', 50))
            ingredients = product.get('ingredients', [])
            image = product.get('image_front_small_url', '')

            good_ingredients = []
            harmful_ingredients = []

            # Ingredients classification (+0.2 points for each)
            for ingredient in ingredients:
                name = ingredient.get('text', '').lower()
                if name in ['milk', 'nuts']:
                    good_ingredients.append(name)
                    eco_score += 0.2
                else:
                    good_ingredients.append(name)
                    eco_score += 0.2

            # Additives penalties (-10 points each)
            additives = product.get('additives_tags', [])
            for additive_tag in additives:
                additive_info = additive_tag.split(":")[-1]
                harmful_ingredients.append(additive_info)
                eco_score -= 10

            # Packaging penalties
            packaging_materials = product.get('packaging', '').lower().split(',')
            if 'plastic' in packaging_materials:
                eco_score -= 10
            elif 'paper' in packaging_materials:
                eco_score += 5

            # Remove duplicates and filter harmful from good
            good_ingredients = list(set(good_ingredients) - set(harmful_ingredients))

            results.append({
                'name': product.get('product_name', product_name),
                'eco_score': round(max(0, min(100, eco_score)), 1),
                'image': image,
                'good_ingredients': good_ingredients,
                'harmful_ingredients': list(set(harmful_ingredients)),
                'packaging': packaging_materials
            })

        return jsonify({'comparison': results})

    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/favicon.ico')
def favicon():
    return '', 204

if __name__ == '__main__':
    app.run(debug=True)
