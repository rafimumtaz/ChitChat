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
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "chat_distributed_db")

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

# Chatroom Endpoints
@app.route('/create-room', methods=['POST'])
def create_room():
    if not request.is_json:
        return jsonify({"status": "error", "message": "Content-Type must be application/json"}), 400

    data = request.get_json()
    room_name = data.get('room_name')
    created_by = data.get('created_by')

    if not room_name or not created_by:
        return jsonify({"status": "error", "message": "Missing required fields: room_name, created_by"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Insert into chatrooms
        sql_room = "INSERT INTO chatrooms (room_name, created_by) VALUES (%s, %s)"
        cursor.execute(sql_room, (room_name, created_by))
        room_id = cursor.lastrowid

        # 2. Insert into room_members
        sql_member = "INSERT INTO room_members (room_id, user_id) VALUES (%s, %s)"
        cursor.execute(sql_member, (room_id, created_by))

        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Chatroom created successfully",
            "data": {
                "room_id": room_id,
                "room_name": room_name,
                "created_by": created_by
            }
        }), 201
    except mysql.connector.Error as err:
        if conn:
            conn.rollback()
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/chatrooms', methods=['GET'])
def get_chatrooms():
    user_id = request.args.get('user_id')

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if user_id:
            # Get rooms where user is a member
            sql = """
                SELECT c.*
                FROM chatrooms c
                JOIN room_members rm ON c.room_id = rm.room_id
                WHERE rm.user_id = %s
            """
            cursor.execute(sql, (user_id,))
        else:
            # Get all rooms
            sql = "SELECT * FROM chatrooms"
            cursor.execute(sql)

        chatrooms = cursor.fetchall()

        # Format chatrooms to match frontend structure (needs messages field to be an array)
        formatted_chatrooms = []
        for room in chatrooms:
             formatted_chatrooms.append({
                 "id": str(room['room_id']),
                 "name": room['room_name'],
                 "topic": "General topic", # Placeholder as topic is not in DB
                 "messages": [] # Fetching messages can be done separately or here if needed, but for list we can send empty or last message
             })

        return jsonify({
            "status": "success",
            "data": formatted_chatrooms
        }), 200
    except mysql.connector.Error as err:
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/messages', methods=['GET'])
def get_messages():
    room_id = request.args.get('room_id')
    if not room_id:
        return jsonify({"status": "error", "message": "Missing room_id"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Join with users to get sender name
        sql = """
            SELECT m.message_id, m.content, m.created_at, m.sender_id, u.username
            FROM messages m
            JOIN users u ON m.sender_id = u.user_id
            WHERE m.room_id = %s
            ORDER BY m.created_at ASC
        """
        cursor.execute(sql, (room_id,))
        messages = cursor.fetchall()

        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "id": str(msg['message_id']),
                "content": msg['content'],
                "timestamp": msg['created_at'].strftime('%I:%M %p') if msg['created_at'] else "",
                "sender": {
                    "id": str(msg['sender_id']),
                    "name": msg['username'],
                    "avatarUrl": f"https://ui-avatars.com/api/?name={msg['username']}",
                    "online": True
                }
            })

        return jsonify({"status": "success", "data": formatted_messages}), 200
    except mysql.connector.Error as err:
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print(" === Application Server (Message Publisher & Auth) Started ===")
    app.run(debug=True, port=5000)
