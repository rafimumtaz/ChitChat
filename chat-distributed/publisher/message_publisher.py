import json
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import pika
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
socketio = SocketIO(app, cors_allowed_origins="*")

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
        # Emit real-time event to the room
        # We need sender info (name/avatar) to display nicely on frontend
        # For simplicity, we can fetch it or pass it.
        # Ideally, we should fetch to be secure/accurate.
        conn = get_db_connection()
        try:
             cursor = conn.cursor(dictionary=True)
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
                "room_id": str(data['room_id'])
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
@socketio.on('connect')
def handle_connect():
    print('Client connected')

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
    room_type = data.get('type', 'group')

    if not room_name or not created_by:
        return jsonify({"status": "error", "message": "Missing required fields: room_name, created_by"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

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
    except mysql.connector.Error as err:
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
        cursor = conn.cursor(dictionary=True)

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
    except mysql.connector.Error as err:
        if conn:
            conn.rollback()
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/chatrooms/add-member', methods=['POST'])
def add_chatroom_member():
    if not request.is_json:
        return jsonify({"status": "error", "message": "Content-Type must be application/json"}), 400

    data = request.get_json()
    room_id = data.get('room_id')
    user_id = data.get('user_id')

    if not room_id or not user_id:
        return jsonify({"status": "error", "message": "Missing room_id or user_id"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if already a member
        check_sql = "SELECT 1 FROM room_members WHERE room_id = %s AND user_id = %s"
        cursor.execute(check_sql, (room_id, user_id))
        if cursor.fetchone():
             return jsonify({"status": "error", "message": "User already in chatroom"}), 409

        # Add member
        sql = "INSERT INTO room_members (room_id, user_id) VALUES (%s, %s)"
        cursor.execute(sql, (room_id, user_id))
        conn.commit()

        # Notify the added user
        socketio.emit('added_to_room', {
            "room_id": str(room_id)
        }, room=f"user_{user_id}")

        return jsonify({"status": "success", "message": "Member added successfully"}), 200
    except mysql.connector.Error as err:
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

        # Format chatrooms
        formatted_chatrooms = []
        for room in chatrooms:
             display_name = room['room_name']

             # If direct chat, find the OTHER user's name
             if room.get('type') == 'direct' and user_id:
                 # Fetch the other member
                 sql_other = """
                    SELECT u.username
                    FROM room_members rm
                    JOIN users u ON rm.user_id = u.user_id
                    WHERE rm.room_id = %s AND rm.user_id != %s
                 """
                 cursor.execute(sql_other, (room['room_id'], user_id))
                 other_user = cursor.fetchone()
                 if other_user:
                     display_name = other_user['username']

             formatted_chatrooms.append({
                 "id": str(room['room_id']),
                 "name": display_name,
                 "topic": "Direct Message" if room.get('type') == 'direct' else "General topic",
                 "type": room.get('type', 'group'),
                 "messages": []
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
        cursor = conn.cursor(dictionary=True)

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
             formatted_users.append({
                 "id": str(u['user_id']),
                 "name": u['username'],
                 "avatarUrl": f"https://ui-avatars.com/api/?name={u['username']}",
                 "online": u['status'] == 'online'
             })

        return jsonify({"status": "success", "data": formatted_users}), 200
    except mysql.connector.Error as err:
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

        # Insert friendship (bidirectional or unidirectional? Usually bidirectional in simple chat apps)
        # Let's do bidirectional for simplicity so both see each other
        sql = "INSERT INTO friends (user_id, friend_id) VALUES (%s, %s), (%s, %s)"
        cursor.execute(sql, (user_id, friend_id, friend_id, user_id))
        conn.commit()

        # Emit event to the friend
        # Need fetch user details to send useful data
        cursor.execute("SELECT username, status FROM users WHERE user_id = %s", (user_id,))
        adder = cursor.fetchone()
        if adder:
            socketio.emit('new_friend', {
                "id": str(user_id),
                "name": adder[0], # Tuple result from standard cursor if not dict=True?
                                  # Wait, get_db_connection().cursor() is default tuple.
                                  # check: line 592 is cursor = conn.cursor() (no dict)
                "avatarUrl": f"https://ui-avatars.com/api/?name={adder[0]}",
                "online": adder[1] == 'online'
            }, room=f"user_{friend_id}")

        return jsonify({"status": "success", "message": "Friend added successfully"}), 201
    except mysql.connector.Error as err:
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
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT u.user_id, u.username, u.status
            FROM users u
            JOIN friends f ON u.user_id = f.friend_id
            WHERE f.user_id = %s
        """
        cursor.execute(sql, (user_id,))
        friends = cursor.fetchall()

        formatted_friends = []
        for f in friends:
             formatted_friends.append({
                 "id": str(f['user_id']),
                 "name": f['username'],
                 "avatarUrl": f"https://ui-avatars.com/api/?name={f['username']}",
                 "online": f['status'] == 'online'
             })

        return jsonify({"status": "success", "data": formatted_friends}), 200
    except mysql.connector.Error as err:
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print(" === Application Server (Message Publisher & Auth) Started ===")
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)
