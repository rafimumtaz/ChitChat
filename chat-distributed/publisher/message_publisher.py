import json
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import pika
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Konfigurasi RabbitMQ
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
RABBITMQ_QUEUE = 'chat_queue'

# Database Configuration (for Auth)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "292006")
DB_NAME = os.getenv("DB_NAME", "chat_distribution_db")

def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )

def publish_message(message_data):
    """
    Menghubungkan ke RabbitMQ dan menerbitkan pesan.
    """
    print(f" [*] Mencoba menerbitkan pesan ke Queue: {RABBITMQ_QUEUE}")
    
    try:
        # 1. Membuat koneksi ke RabbitMQ
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()

        # 2. Mendeklarasikan Queue
        channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)

        # 3. Menerbitkan Pesan (Publisher)
        channel.basic_publish(
            exchange="chat_exchange",           
            routing_key="chat.message",         
            body=json.dumps(message_data),
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent
            )
        )
        print(f" [x] Pesan berhasil diterbitkan ke RabbitMQ.")

        # 4. Menutup koneksi
        connection.close()
        return True

    except pika.exceptions.AMQPConnectionError as e:
        print(f" [!] GAGAL menghubungkan atau menerbitkan ke RabbitMQ: {e}")
        return False
    except Exception as e:
        print(f" [!] Error umum saat menerbitkan pesan: {e}")
        return False

# API Endpoint (Application Layer)
@app.route('/send-message', methods=['POST'])
def send_message():
    """
    Menerima request POST dari Client Browser dan menerbitkannya ke Message Broker.
    """
    if not request.is_json:
        return jsonify({"status": "error", "message": "Content-Type must be application/json"}), 400

    data = request.get_json()
    
    # Validasi data wajib (sesuai skema MESSAGES di ERD)
    required_fields = ['sender_id', 'room_id', 'content']
    if not all(field in data for field in required_fields):
        return jsonify({"status": "error", "message": "Missing required fields (sender_id, room_id, content)"}), 400

    # Add optional fields if missing
    if 'publisher_msg_id' not in data:
         import uuid
         data['publisher_msg_id'] = str(uuid.uuid4())
    if 'seq' not in data:
         data['seq'] = 0


    # Panggil fungsi publisher
    if publish_message(data):
        return jsonify({
            "status": "accepted", 
            "message": "Message successfully handed over to RabbitMQ",
            "next_step": "Waiting for Consumer Service to process and store in DB"
        }), 202
    else:
        return jsonify({"status": "error", "message": "Message Broker is unavailable. Try again later."}), 503

# Auth Endpoints
@app.route('/register', methods=['POST'])
def register():
    if not request.is_json:
        return jsonify({"status": "error", "message": "Content-Type must be application/json"}), 400

    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
         return jsonify({"status": "error", "message": "Missing required fields"}), 400

    hashed_password = generate_password_hash(password)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = "INSERT INTO users (username, email, password, status) VALUES (%s, %s, %s, 'offline')"
        cursor.execute(sql, (username, email, hashed_password))
        conn.commit()

        return jsonify({"status": "success", "message": "User registered successfully"}), 201
    except mysql.connector.Error as err:
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/login', methods=['POST'])
def login():
    if not request.is_json:
        return jsonify({"status": "error", "message": "Content-Type must be application/json"}), 400

    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
         return jsonify({"status": "error", "message": "Missing required fields"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        sql = "SELECT * FROM users WHERE email = %s"
        cursor.execute(sql, (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            # Update status to online
            update_sql = "UPDATE users SET status = 'online' WHERE user_id = %s"
            cursor.execute(update_sql, (user['user_id'],))
            conn.commit()

            return jsonify({
                "status": "success",
                "message": "Login successful",
                "user": {
                    "user_id": user['user_id'],
                    "username": user['username'],
                    "email": user['email'],
                    "status": "online"
                }
            }), 200
        else:
            return jsonify({"status": "error", "message": "Invalid credentials"}), 401
    except mysql.connector.Error as err:
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print(" === Application Server (Message Publisher & Auth) Started ===")
    app.run(debug=True, port=5000)
