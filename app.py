import os
import pymysql
from decimal import Decimal
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint
from flask import Flask, request, jsonify, send_from_directory, url_for

import logging
from datetime import datetime

app = Flask(__name__)
CORS(app, origins="http://localhost:3000", methods=["GET", "POST"])

logging.basicConfig(level=logging.INFO)

@app.before_request
def before_request_logging():
    request.start_time = datetime.now()
    logging.info(f"Incoming request: {request.method} {request.path}")

@app.after_request
def after_request_logging(response):
    duration = datetime.now() - request.start_time
    duration_ms = int(duration.total_seconds() * 1000)
    
    logging.info(
        f"Completed request: {request.method} {request.path} "
        f"Status: {response.status_code} Duration: {duration_ms}ms"
    )
    return response

SWAGGER_URL = '/docs'
API_URL = '/openapi.yaml'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name': "Product API"}
)

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

@app.route('/openapi.yaml')
def serve_openapi_spec():
    return send_from_directory(os.getcwd(), 'openapi.yaml')

db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'port': int(os.getenv('DB_PORT', 3306))  # Default port is 3306 if not provided
}

def fetch_from_db(query, params=None):
    conn = None
    try:
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        return results
    except pymysql.MySQLError as err:
        return f"Error: {err}"
    finally:
        if conn:
            cursor.close()
            conn.close()

def insert_into_db(query, params):
    conn = None
    try:
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return "Success"
    except pymysql.MySQLError as err:
        return f"Error: {err}"
    finally:
        if conn:
            cursor.close()
            conn.close()

@app.route('/search_product', methods=['GET'])
def search_product():
    product_name = request.args.get('product_name')
    page = int(request.args.get('page', 1))  # Default to page 1 if not provided
    per_page = int(request.args.get('per_page', 6))  # Default to 6 items per page
    
    if not product_name:
        return jsonify({"error": "product_name parameter is required"}), 400

    offset = (page - 1) * per_page
    query = "SELECT * FROM Products WHERE LOWER(product_name) LIKE %s LIMIT %s OFFSET %s"
    params = (f"%{product_name.strip().lower()}%", per_page, offset)

    results = fetch_from_db(query, params)

    if isinstance(results, str):
        return jsonify({"error": results}), 500

    result_list = []
    for row in results:
        product = {
            "product_id": row[0],
            "product_name": row[1],
            "price": float(row[2]) if isinstance(row[2], Decimal) else row[2],
            "quantity": row[3],
            "description": row[4],
            "image_url": row[5],
            "is_sold": row[6],
            "created_at": row[7].strftime('%Y-%m-%d %H:%M:%S'),
            "seller_id": row[8]
        }
        product['links'] = [
            {"rel": "self", "href": url_for('search_product', product_name=product_name, _external=True)},
            {"rel": "update", "href": url_for('post_product', _external=True)},
            {"rel": "delete", "href": url_for('delete_product', product_id=row[0], _external=True)}
        ]
        result_list.append(product)
    
    return jsonify(result_list), 200

@app.route('/search_products_by_user_id', methods=['GET'])
def search_orders_by_id():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id parameter is required"}), 400
    query = "SELECT * FROM Products WHERE seller_id = %s"
    params = (user_id,)
    results = fetch_from_db(query, params)
    if isinstance(results, str):
        return jsonify({"error": results}), 500
    if not results:
        return jsonify({"message": "No orders found for this user ID"}), 404
    result_list = []
    for row in results:
        result_list.append({
            "product_id": row[0],
            "product_name": row[1],
            "price": float(row[2]) if isinstance(row[2], Decimal) else row[2],
            "quantity": row[3],
            "description": row[4],
            "image_url": row[5],
            "is_sold": row[6],
            "created_at": row[7].strftime('%Y-%m-%d %H:%M:%S'),
            "seller_id": row[8]
        })
    return jsonify({'products': result_list}), 200

@app.route('/post_product', methods=['POST'])
def post_product():
    data = request.json
    required_fields = ["product_name", "price", "quantity", "description", "image_url", "seller_id"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400
    query = """
    INSERT INTO Products (product_name, price, quantity, description, image_url, is_sold, seller_id)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        data["product_name"],
        data["price"],
        data["quantity"],
        data["description"],
        data["image_url"],
        0,
        data["seller_id"]
    )
    result = insert_into_db(query, params)
    if result == "Success":
        return jsonify({"message": "New product added"}), 201
    else:
        return jsonify({"error": result}), 500

@app.route('/delete_product', methods=['DELETE'])
def delete_product():
    product_id = request.args.get('product_id')
    
    if not product_id:
        return jsonify({"error": "product_id parameter is required"}), 400
    
    delete_product_query = "DELETE FROM Products WHERE product_id = %s"
    
    result_product = insert_into_db(delete_product_query, (product_id,))
    if result_product == "Success":
        return jsonify({"message": f"Product with ID {product_id} deleted successfully"}), 200
    else:
        return jsonify({"error": result_product}), 500



if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8888, debug=True)