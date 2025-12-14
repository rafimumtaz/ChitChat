import json
import os
import uuid
import mimetypes
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pika
import pymysql
import pymysql.cursors
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit, join_room, leave_room
import redis
from socket_events import register_socket_events
from gcs_handler import upload_to_gcs

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for all routes

# Konfigurasi RabbitMQ
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')

# Configure SocketIO to use RabbitMQ as message queue for cross-process emitting
# Use threading mode to avoid conflict with pika BlockingConnection and eventlet
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', message_queue=f'amqp://guest:guest@{RABBITMQ_HOST}:5672//')
RABBITMQ_QUEUE = 'chat_queue'

# Redis Configuration
r_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
register_socket_events(socketio, r_client)

# Database Configuration (for Auth)
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "chat_distributed_db")

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
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

# File Upload Endpoint
@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400

    if file:
        filename = secure_filename(file.filename)
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}_{filename}"

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
             mime_type = file.content_type or 'application/octet-stream'

        try:
            file_url = upload_to_gcs(file, unique_filename, mime_type)

            return jsonify({
                "status": "success",
                "file_url": file_url,
                "file_type": mime_type,
                "original_name": filename
            }), 201
        except Exception as e:
            print(f"Upload error: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

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
         data['publisher_msg_id'] = str(uuid.uuid4())
    if 'seq' not in data:
         data['seq'] = 0

    # File attachments
    # data can have attachment_url, attachment_type, original_name from frontend if uploaded first

    # Panggil fungsi publisher
    if publish_message(data):
        # Emit real-time event to the room
        # We need sender info (name/avatar) to display nicely on frontend
        # For simplicity, we can fetch it or pass it.
        # Ideally, we should fetch to be secure/accurate.
        conn = get_db_connection()
        try:
             cursor = conn.cursor(pymysql.cursors.DictCursor)
             cursor.execute("SELECT username FROM users WHERE user_id = %s", (data['sender_id'],))
             sender_user = cursor.fetchone()
             sender_name = sender_user['username'] if sender_user else "Unknown"

             socket_message = {
                "id": data['publisher_msg_id'],
                "content": data['content'],
                "timestamp": "Just now", # Frontend can format
                "sender": {
                    "id": str(data['sender_id']),
                    "name": sender_name,
                    "avatarUrl": f"https://ui-avatars.com/api/?name={sender_name}",
                    "online": True
                },
                "room_id": str(data['room_id']),
                "attachment_url": data.get('attachment_url'),
                "attachment_type": data.get('attachment_type'),
                "original_name": data.get('original_name')
             }
             socketio.emit('new_message', socket_message, room=f"room_{data['room_id']}")
        except Exception as e:
             print(f"Socket emit failed: {e}")
        finally:
             if conn: conn.close()

        return jsonify({
            "status": "accepted", 
            "message": "Message successfully handed over to RabbitMQ",
            "next_step": "Waiting for Consumer Service to process and store in DB"
        }), 202
    else:
        return jsonify({"status": "error", "message": "Message Broker is unavailable. Try again later."}), 503

# SocketIO Events
# connect event is handled in socket_events.py

@socketio.on('join_user_room')
def handle_join_user_room(data):
    user_id = data.get('user_id')
    if user_id:
        join_room(f"user_{user_id}")
        print(f"User {user_id} joined room user_{user_id}")

@socketio.on('join_room')
def handle_join_room(data):
    room_id = data.get('room_id')
    if room_id:
        join_room(f"room_{room_id}")
        print(f"Client joined room_{room_id}")

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
    except pymysql.MySQLError as err:
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/room/<room_id>', methods=['DELETE'])
def delete_room(room_id):
    if not request.is_json:
        return jsonify({"status": "error", "message": "Content-Type must be application/json"}), 400

    data = request.get_json()
    current_user_id = data.get('current_user_id')

    if not current_user_id:
        return jsonify({"status": "error", "message": "Missing current_user_id"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # 1. Verify Admin Status
        sql_room = "SELECT created_by FROM chatrooms WHERE room_id = %s"
        cursor.execute(sql_room, (room_id,))
        room = cursor.fetchone()

        if not room:
            return jsonify({"status": "error", "message": "Room not found"}), 404

        if str(room['created_by']) != str(current_user_id):
            return jsonify({"status": "error", "message": "Unauthorized: Only admin can delete room"}), 403

        # 2. Delete Room (Cascades to messages and members)
        sql_delete = "DELETE FROM chatrooms WHERE room_id = %s"
        cursor.execute(sql_delete, (room_id,))
        conn.commit()

        # Notify members (optional but good)
        # We can't query members after delete, so ideally fetch before.
        # But socket rooms work by ID, so emitting to room_{id} might not reach anyone if connection closed?
        # Actually client keeps connection open.
        socketio.emit('room_deleted', {
            "room_id": str(room_id)
        }, room=f"room_{room_id}")

        return jsonify({"status": "success", "message": "Room deleted successfully"}), 200

    except pymysql.MySQLError as err:
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/room/<room_id>/messages', methods=['DELETE'])
def clear_chat(room_id):
    if not request.is_json:
        return jsonify({"status": "error", "message": "Content-Type must be application/json"}), 400

    data = request.get_json()
    current_user_id = data.get('current_user_id')

    if not current_user_id:
        return jsonify({"status": "error", "message": "Missing current_user_id"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # 1. Verify Admin Status
        sql_room = "SELECT created_by FROM chatrooms WHERE room_id = %s"
        cursor.execute(sql_room, (room_id,))
        room = cursor.fetchone()

        if not room:
            return jsonify({"status": "error", "message": "Room not found"}), 404

        if str(room['created_by']) != str(current_user_id):
            return jsonify({"status": "error", "message": "Unauthorized: Only admin can clear chat"}), 403

        # 2. Delete Messages
        sql_delete = "DELETE FROM messages WHERE room_id = %s"
        cursor.execute(sql_delete, (room_id,))
        conn.commit()

        # Notify
        socketio.emit('chat_cleared', {
            "room_id": str(room_id)
        }, room=f"room_{room_id}")

        return jsonify({"status": "success", "message": "Chat cleared successfully"}), 200

    except pymysql.MySQLError as err:
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
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        sql = "SELECT * FROM users WHERE email = %s"
        cursor.execute(sql, (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            # Status managed by Redis events
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
    except pymysql.MySQLError as err:
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/logout', methods=['POST'])
def logout():
    if not request.is_json:
        return jsonify({"status": "error", "message": "Content-Type must be application/json"}), 400

    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
         return jsonify({"status": "error", "message": "Missing user_id"}), 400

    conn = None
    try:
        # Status managed by Redis events (disconnect)
        return jsonify({"status": "success", "message": "Logged out successfully"}), 200
    except pymysql.MySQLError as err:
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
    room_type = data.get('type', 'group')

    if not room_name or not created_by:
        return jsonify({"status": "error", "message": "Missing required fields: room_name, created_by"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # 1. Insert into chatrooms
        sql_room = "INSERT INTO chatrooms (room_name, created_by, type) VALUES (%s, %s, %s)"
        cursor.execute(sql_room, (room_name, created_by, room_type))
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
                "type": room_type,
                "created_by": created_by
            }
        }), 201
    except pymysql.MySQLError as err:
        if conn:
            conn.rollback()
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/private-chat', methods=['POST'])
def start_private_chat():
    if not request.is_json:
        return jsonify({"status": "error", "message": "Content-Type must be application/json"}), 400

    data = request.get_json()
    user_id = data.get('user_id')
    friend_id = data.get('friend_id')

    if not user_id or not friend_id:
        return jsonify({"status": "error", "message": "Missing user_id or friend_id"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # 1. Check if a direct room already exists
        # We find a room of type 'direct' where both users are members.
        sql_check = """
            SELECT c.room_id, c.room_name
            FROM chatrooms c
            JOIN room_members rm1 ON c.room_id = rm1.room_id
            JOIN room_members rm2 ON c.room_id = rm2.room_id
            WHERE c.type = 'direct'
            AND rm1.user_id = %s
            AND rm2.user_id = %s
            LIMIT 1
        """
        cursor.execute(sql_check, (user_id, friend_id))
        existing_room = cursor.fetchone()

        if existing_room:
             return jsonify({
                 "status": "success",
                 "message": "Private chat exists",
                 "data": {
                     "room_id": existing_room['room_id'],
                     "room_name": existing_room['room_name'],
                     "type": 'direct'
                 }
             }), 200

        # 2. Create new direct room
        # For direct rooms, room_name isn't strictly displayed, but we need a value.
        # We can use a unique string like "direct_<id>_<id>"
        room_name = f"direct_{min(user_id, friend_id)}_{max(user_id, friend_id)}"

        sql_create = "INSERT INTO chatrooms (room_name, created_by, type) VALUES (%s, %s, 'direct')"
        cursor.execute(sql_create, (room_name, user_id))
        room_id = cursor.lastrowid

        # 3. Add both members
        sql_members = "INSERT INTO room_members (room_id, user_id) VALUES (%s, %s), (%s, %s)"
        cursor.execute(sql_members, (room_id, user_id, room_id, friend_id))

        conn.commit()

        # Emit event to the friend so they see the new chat immediately
        socketio.emit('new_private_chat', {
            "room_id": str(room_id),
            "room_name": room_name, # Frontend will need to swap name likely, or we send generic
            "type": 'direct',
            "initiator_id": str(user_id)
        }, room=f"user_{friend_id}")

        return jsonify({
            "status": "success",
            "message": "Private chat started",
            "data": {
                "room_id": room_id,
                "room_name": room_name,
                "type": 'direct'
            }
        }), 201
    except pymysql.MySQLError as err:
        if conn:
            conn.rollback()
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/chatrooms/invite', methods=['POST'])
def invite_to_room():
    if not request.is_json:
        return jsonify({"status": "error", "message": "Content-Type must be application/json"}), 400

    data = request.get_json()
    room_id = data.get('room_id')
    user_id = data.get('user_id') # invitee
    sender_id = data.get('sender_id') # inviter (Admin)

    if not room_id or not user_id or not sender_id:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if already a member
        check_sql = "SELECT 1 FROM room_members WHERE room_id = %s AND user_id = %s"
        cursor.execute(check_sql, (room_id, user_id))
        if cursor.fetchone():
             return jsonify({"status": "error", "message": "User already in chatroom"}), 409

        # Fetch details for notification message
        cursor.execute("SELECT username FROM users WHERE user_id = %s", (sender_id,))
        sender = cursor.fetchone()
        sender_name = sender['username'] if sender else "Unknown"

        cursor.execute("SELECT room_name FROM chatrooms WHERE room_id = %s", (room_id,))
        room = cursor.fetchone()
        room_name = room['room_name'] if room else "Chatroom"

        # Publish to RabbitMQ
        msg = {
            'type': 'GROUP_INVITE',
            'sender_id': sender_id,
            'receiver_id': user_id,
            'room_id': room_id,
            'sender_name': sender_name,
            'room_name': room_name
        }

        if publish_message(msg):
            return jsonify({"status": "success", "message": "Invitation sent"}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to send invitation"}), 503

    except pymysql.MySQLError as err:
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
        cursor = conn.cursor(pymysql.cursors.DictCursor)

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

        # Format chatrooms
        formatted_chatrooms = []
        for room in chatrooms:
             display_name = room['room_name']

             # If direct chat, find the OTHER user's name
             other_user_id_str = None
             if room.get('type') == 'direct' and user_id:
                 # Fetch the other member
                 sql_other = """
                    SELECT u.username, u.user_id
                    FROM room_members rm
                    JOIN users u ON rm.user_id = u.user_id
                    WHERE rm.room_id = %s AND rm.user_id != %s
                 """
                 cursor.execute(sql_other, (room['room_id'], user_id))
                 other_user = cursor.fetchone()
                 if other_user:
                     display_name = other_user['username']
                     other_user_id_str = str(other_user['user_id'])

             formatted_chatrooms.append({
                 "id": str(room['room_id']),
                 "name": display_name,
                 "otherUserId": other_user_id_str,
                 "topic": "Direct Message" if room.get('type') == 'direct' else "General topic",
                 "type": room.get('type', 'group'),
                 "messages": []
             })

        return jsonify({
            "status": "success",
            "data": formatted_chatrooms
        }), 200
    except pymysql.MySQLError as err:
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
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Join with users to get sender name
        sql = """
            SELECT m.message_id, m.content, m.created_at, m.sender_id, u.username,
                   m.attachment_url, m.attachment_type, m.original_name
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
                },
                "attachment_url": msg.get('attachment_url'),
                "attachment_type": msg.get('attachment_type'),
                "original_name": msg.get('original_name')
            })

        return jsonify({"status": "success", "data": formatted_messages}), 200
    except pymysql.MySQLError as err:
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if conn:
            conn.close()

# Friend Endpoints
@app.route('/users/search', methods=['GET'])
def search_users():
    query = request.args.get('query', '')
    current_user_id = request.args.get('user_id')
    include_friends = request.args.get('include_friends', 'false').lower() == 'true'

    if not current_user_id:
         return jsonify({"status": "error", "message": "Missing user_id"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Search users not strictly matching query but excluding current user
        # Conditionally exclude friends
        sql = """
            SELECT u.user_id, u.username, u.status
            FROM users u
            WHERE u.user_id != %s
            AND u.username LIKE %s
        """
        params = [current_user_id, f"%{query}%"]

        if not include_friends:
             sql += " AND u.user_id NOT IN (SELECT friend_id FROM friends WHERE user_id = %s)"
             params.append(current_user_id)

        sql += " LIMIT 20"

        cursor.execute(sql, tuple(params))
        users = cursor.fetchall()

        formatted_users = []
        for u in users:
             is_online = r_client.get(f"presence:user:{u['user_id']}") == "online"
             formatted_users.append({
                 "id": str(u['user_id']),
                 "name": u['username'],
                 "avatarUrl": f"https://ui-avatars.com/api/?name={u['username']}",
                 "online": is_online
             })

        return jsonify({"status": "success", "data": formatted_users}), 200
    except pymysql.MySQLError as err:
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/friends', methods=['POST'])
def add_friend():
    if not request.is_json:
        return jsonify({"status": "error", "message": "Content-Type must be application/json"}), 400

    data = request.get_json()
    user_id = data.get('user_id')
    friend_id = data.get('friend_id')

    if not user_id or not friend_id:
        return jsonify({"status": "error", "message": "Missing user_id or friend_id"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if already friends
        check_sql = "SELECT 1 FROM friends WHERE user_id = %s AND friend_id = %s"
        cursor.execute(check_sql, (user_id, friend_id))
        if cursor.fetchone():
             return jsonify({"status": "error", "message": "Already friends"}), 409

        # Fetch sender name for notification
        cursor.execute("SELECT username FROM users WHERE user_id = %s", (user_id,))
        sender = cursor.fetchone()
        sender_name = sender['username'] if sender else "Unknown"

        # Publish to RabbitMQ
        msg = {
            'type': 'FRIEND_REQUEST',
            'sender_id': user_id,
            'receiver_id': friend_id,
            'sender_name': sender_name
        }

        if publish_message(msg):
            return jsonify({"status": "success", "message": "Friend request processed"}), 201
        else:
            return jsonify({"status": "error", "message": "Failed to send request"}), 503

    except pymysql.MySQLError as err:
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/friends', methods=['GET'])
def get_friends():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Missing user_id"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        sql = """
            SELECT u.user_id, u.username, u.status
            FROM users u
            JOIN friends f ON u.user_id = f.friend_id
            WHERE f.user_id = %s AND f.status = 'ACCEPTED'
            UNION
            SELECT u.user_id, u.username, u.status
            FROM users u
            JOIN friends f ON u.user_id = f.user_id
            WHERE f.friend_id = %s AND f.status = 'ACCEPTED'
        """
        cursor.execute(sql, (user_id, user_id))
        friends = cursor.fetchall()

        formatted_friends = []
        for f in friends:
             is_online = r_client.get(f"presence:user:{f['user_id']}") == "online"
             last_seen = r_client.get(f"last_seen:user:{f['user_id']}")
             formatted_friends.append({
                 "id": str(f['user_id']),
                 "name": f['username'],
                 "avatarUrl": f"https://ui-avatars.com/api/?name={f['username']}",
                 "online": is_online,
                 "lastSeen": last_seen
             })

        return jsonify({"status": "success", "data": formatted_friends}), 200
    except pymysql.MySQLError as err:
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/room/<room_id>/info', methods=['GET'])
def get_room_info(room_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # 1. Fetch Room Info & Admin
        sql_room = """
            SELECT c.room_name, c.created_by, u.username as admin_name
            FROM chatrooms c
            LEFT JOIN users u ON c.created_by = u.user_id
            WHERE c.room_id = %s
        """
        cursor.execute(sql_room, (room_id,))
        room = cursor.fetchone()

        if not room:
            return jsonify({"status": "error", "message": "Room not found"}), 404

        # 2. Fetch Members
        sql_members = """
            SELECT u.user_id, u.username, u.status
            FROM room_members rm
            JOIN users u ON rm.user_id = u.user_id
            WHERE rm.room_id = %s
        """
        cursor.execute(sql_members, (room_id,))
        members = cursor.fetchall()

        formatted_members = []
        for m in members:
            is_online = r_client.get(f"presence:user:{m['user_id']}") == "online"
            formatted_members.append({
                "id": str(m['user_id']),
                "name": m['username'],
                "avatarUrl": f"https://ui-avatars.com/api/?name={m['username']}",
                "online": is_online
            })

        return jsonify({
            "status": "success",
            "data": {
                "room_name": room['room_name'],
                "created_by": str(room['created_by']),
                "admin_name": room['admin_name'],
                "members": formatted_members
            }
        }), 200

    except pymysql.MySQLError as err:
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/room/<room_id>/kick', methods=['POST'])
def kick_member(room_id):
    if not request.is_json:
        return jsonify({"status": "error", "message": "Content-Type must be application/json"}), 400

    data = request.get_json()
    user_id_to_kick = data.get('user_id')
    current_user_id = data.get('current_user_id')

    if not user_id_to_kick or not current_user_id:
        return jsonify({"status": "error", "message": "Missing user_id or current_user_id"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # 1. Verify Admin Status
        sql_room = "SELECT created_by FROM chatrooms WHERE room_id = %s"
        cursor.execute(sql_room, (room_id,))
        room = cursor.fetchone()

        if not room:
            return jsonify({"status": "error", "message": "Room not found"}), 404

        # Check authorization: Requester must be the creator
        if str(room['created_by']) != str(current_user_id):
            return jsonify({"status": "error", "message": "Unauthorized: Only admin can kick members"}), 403

        # 2. Delete Member
        sql_delete = "DELETE FROM room_members WHERE room_id = %s AND user_id = %s"
        cursor.execute(sql_delete, (room_id, user_id_to_kick))
        conn.commit()

        # Notify the kicked user and others
        socketio.emit('member_kicked', {
            "room_id": str(room_id),
            "user_id": str(user_id_to_kick)
        }, room=f"room_{room_id}")

        return jsonify({"status": "success", "message": "User kicked successfully"}), 200

    except pymysql.MySQLError as err:
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/notifications', methods=['GET'])
def get_notifications():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Missing user_id"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        sql = """
            SELECT n.notif_id, n.type, n.reference_id, n.status, u.username as sender_name, c.room_name
            FROM notifications n
            JOIN users u ON n.sender_id = u.user_id
            LEFT JOIN chatrooms c ON n.reference_id = c.room_id AND n.type = 'GROUP_INVITE'
            WHERE n.receiver_id = %s AND n.status != 'read'
            ORDER BY n.sent_at DESC
        """
        cursor.execute(sql, (user_id,))
        notifs = cursor.fetchall()

        return jsonify({"status": "success", "data": notifs}), 200
    except pymysql.MySQLError as err:
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/notifications/<notif_id>/respond', methods=['POST'])
def respond_notification(notif_id):
    if not request.is_json:
        return jsonify({"status": "error", "message": "Content-Type must be application/json"}), 400

    data = request.get_json()
    action = data.get('action') # ACCEPT or REJECT

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Get notification details
        cursor.execute("SELECT * FROM notifications WHERE notif_id = %s", (notif_id,))
        notif = cursor.fetchone()

        if not notif:
            return jsonify({"status": "error", "message": "Notification not found"}), 404

        if action == 'ACCEPT':
            if notif['type'] == 'FRIEND_REQUEST':
                # Fetch sender name (initiator)
                cursor.execute("SELECT username FROM users WHERE user_id = %s", (notif['sender_id'],))
                sender = cursor.fetchone()
                sender_name = sender['username']

                # Fetch acceptor name (current user)
                cursor.execute("SELECT username FROM users WHERE user_id = %s", (notif['receiver_id'],))
                acceptor = cursor.fetchone()
                acceptor_name = acceptor['username']

                # Publish FRIEND_ACCEPTED
                msg = {
                    'type': 'FRIEND_ACCEPTED',
                    'initiator_id': notif['sender_id'], # Original sender of request
                    'acceptor_id': notif['receiver_id'], # Current user accepting
                    'sender_name': sender_name,
                    'acceptor_name': acceptor_name,
                    'notif_id': notif_id
                }
                publish_message(msg)

            elif notif['type'] == 'GROUP_INVITE':
                 # Fetch acceptor name (current user)
                 cursor.execute("SELECT username FROM users WHERE user_id = %s", (notif['receiver_id'],))
                 acceptor = cursor.fetchone()
                 acceptor_name = acceptor['username'] if acceptor else "Unknown"

                 # Publish GROUP_JOINED
                 msg = {
                     'type': 'GROUP_JOINED',
                     'room_id': notif['reference_id'],
                     'user_id': notif['receiver_id'],
                     'inviter_id': notif['sender_id'],
                     'acceptor_name': acceptor_name,
                     'notif_id': notif_id
                 }
                 publish_message(msg)

        elif action == 'REJECT':
            # Just update notif status
            cursor.execute("UPDATE notifications SET status = 'read' WHERE notif_id = %s", (notif_id,))
            conn.commit()

        return jsonify({"status": "success", "message": f"Request {action.lower()}ed"}), 200

    except pymysql.MySQLError as err:
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/friends/<friend_id>', methods=['DELETE'])
def remove_friend(friend_id):
    if not request.is_json:
        return jsonify({"status": "error", "message": "Content-Type must be application/json"}), 400

    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({"status": "error", "message": "Missing user_id"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Delete friendship (bidirectional check)
        sql = "DELETE FROM friends WHERE (user_id = %s AND friend_id = %s) OR (user_id = %s AND friend_id = %s)"
        cursor.execute(sql, (user_id, friend_id, friend_id, user_id))
        conn.commit()

        return jsonify({"status": "success", "message": "Friend removed successfully"}), 200
    except pymysql.MySQLError as err:
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print(" === Application Server (Message Publisher & Auth) Started ===")
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)
