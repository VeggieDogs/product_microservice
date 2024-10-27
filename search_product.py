from flask import Flask, request, jsonify
import pymysql
from flask_cors import CORS
from decimal import Decimal

app = Flask(__name__)
CORS(app, origins="http://localhost:3000", methods=["GET", "POST"])

db_config = {
    'host': '52.90.112.251',  # Replace with the external IP of your MySQL VM
    'user': 'admin',             # MySQL user you created
    'password': 'dbuserdbuser',  # The password for the MySQL user
    'database': 'products',         # The name of your database
    'port': 3306                 # Default MySQL port
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
    
    if not product_name:
        return jsonify({"error": "product_name parameter is required"}), 400

    query = "SELECT * FROM Products WHERE product_name LIKE %s"
    params = (f"%{product_name}%",)

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
        0,  # Assuming is_sold is 0 (not sold) by default
        data["seller_id"]
    )

    result = insert_into_db(query, params)
    if result == "Success":
        return jsonify({"message": "Product posted successfully"}), 201
    else:
        return jsonify({"error": result}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8888, debug=True)
