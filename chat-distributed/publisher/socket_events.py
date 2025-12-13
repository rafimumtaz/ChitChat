from flask import request
from flask_socketio import emit, join_room, leave_room
import time
from datetime import datetime

def register_socket_events(socketio, redis_client):

    # Store user_id in a way accessible during disconnect
    # We can use a simple global dict for mapping sid -> user_id
    # Since we are using threading mode, this is shared memory.
    sid_to_user = {}

    @socketio.on('connect')
    def handle_connect():
        user_id = request.args.get('user_id')
        if not user_id:
            # Check if user_id is in handshake query (sometimes request.args works for HTTP requests but for WS might need request.sid inspection or handshake)
            # In Flask-SocketIO, request.args contains the query string arguments of the connection URL.
            print("Connect attempt without user_id")
            return

        print(f"User {user_id} connected (SID: {request.sid})")

        # Store mapping
        sid_to_user[request.sid] = user_id

        # Set Redis Presence
        redis_client.set(f"presence:user:{user_id}", "online")

        # Join user room (Existing logic in message_publisher.py uses 'join_user_room' event,
        # but we can do it here too for robustness)
        join_room(f"user_{user_id}")

        # Broadcast Status
        emit('user_status_change', {'user_id': user_id, 'status': 'online'}, broadcast=True)

    @socketio.on('disconnect')
    def handle_disconnect(reason=None):
        user_id = sid_to_user.get(request.sid)
        if user_id:
            # Remove presence
            redis_client.delete(f"presence:user:{user_id}")

            # Set Last Seen
            last_seen = datetime.now().isoformat()
            redis_client.set(f"last_seen:user:{user_id}", last_seen)

            # Broadcast Status
            emit('user_status_change', {
                'user_id': user_id,
                'status': 'offline',
                'last_seen': last_seen
            }, broadcast=True)

            print(f"User {user_id} disconnected")
            del sid_to_user[request.sid]

    @socketio.on('typing_start')
    def handle_typing_start(data):
        user_id = sid_to_user.get(request.sid)
        room_id = data.get('room_id')
        if user_id and room_id:
            key = f"typing:room:{room_id}:user:{user_id}"
            redis_client.setex(key, 3, "1")

            # Emit to room (exclude sender)
            emit('display_typing', {
                'user_id': user_id,
                'room_id': room_id
            }, room=f"room_{room_id}", include_self=False)

    @socketio.on('typing_stop')
    def handle_typing_stop(data):
        user_id = sid_to_user.get(request.sid)
        room_id = data.get('room_id')
        if user_id and room_id:
            key = f"typing:room:{room_id}:user:{user_id}"
            redis_client.delete(key)

            emit('hide_typing', {
                'user_id': user_id,
                'room_id': room_id
            }, room=f"room_{room_id}", include_self=False)
