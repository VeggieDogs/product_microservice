from flask import Flask, request, jsonify, send_from_directory
from flask_swagger_ui import get_swaggerui_blueprint
import os
import pymysql
from flask_cors import CORS
from decimal import Decimal

app = Flask(__name__)
CORS(app, origins="http://localhost:3000", methods=["GET", "POST"])

SWAGGER_URL = '/docs'
API_URL = '/openapi.yaml'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name': "Product and Orders API"}
)

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

@app.route('/openapi.yaml')
def serve_openapi_spec():
    return send_from_directory(os.getcwd(), 'openapi.yaml')

db_config = {
    'host': '52.90.112.251',
    'user': 'admin',
    'password': 'dbuserdbuser',
    'database': 'products',
    'port': 3306
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
        result_list.append({
            "product_id": row[0],
            "product_name": row[1],
            "price": float(row[2]) if isinstance(row[2], Decimal) else row[2],
            "quantity": row[3],
            "description": row[4],
            "image_url": row[5],
            "is_sold": row[6],
            "created_at": row[7].strftime('%Y-%m-%d %H:%M:%S')
        })
    print(result_list)
    return jsonify(result_list), 200

@app.route('/search_orders_by_id', methods=['GET'])
def search_orders_by_id():
    user_id = request.args.get('user_id')
    role = request.args.get('role')
    if not user_id:
        return jsonify({"error": "user_id parameter is required"}), 400
    if role == 'seller':
        query = "SELECT * FROM Orders WHERE seller_id = %s"
        params = (user_id,)
        results = fetch_from_db(query, params)
    elif role == 'buyer':
        query = "SELECT * FROM Orders WHERE buyer_id = %s"
        params = (user_id,)
        results = fetch_from_db(query, params)
    else:
        query = """
            (SELECT * FROM Orders WHERE seller_id = %s)
            UNION
            (SELECT * FROM Orders WHERE buyer_id = %s)
        """
        params = (user_id, user_id)
        results = fetch_from_db(query, params)
    if isinstance(results, str):
        return jsonify({"error": results}), 500
    if not results:
        return jsonify({"message": "No orders found for this user ID"}), 404
    result_list = []
    for row in results:
        result_list.append({
            "order_id": row[0],
            "quantity": row[1],
            "total_price": float(row[2]),
            "purchase_time": row[3].strftime('%Y-%m-%d %H:%M:%S') if row[3] else None,
            "status": row[4],
            "seller_id": row[5],
            "buyer_id": row[6],
            "product_id": row[7],
            "created_at": row[8].strftime('%Y-%m-%d %H:%M:%S') if row[8] else None
        })
    return jsonify(result_list), 200

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

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8888, debug=True)
