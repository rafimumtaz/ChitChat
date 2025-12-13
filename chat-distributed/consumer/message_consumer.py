import pika
import json
import sys
import os
from flask_socketio import SocketIO

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database_writer.db_writer import (
    write_message,
    write_friend_request,
    write_friend_accept,
    write_group_invite,
    write_group_join
)

# Konfigurasi RabbitMQ
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
QUEUE_NAME = 'chat_queue'

# SocketIO for emitting events
# We use the message_queue to publish to the external queue that the Flask server listens to.
socketio = SocketIO(message_queue=f'amqp://guest:guest@{RABBITMQ_HOST}:5672//')

def callback(ch, method, properties, body):
    try:
        message = json.loads(body)
        print("Received message:", message)

        msg_type = message.get('type')

        success = False

        if msg_type == 'FRIEND_REQUEST':
            if write_friend_request(message):
                # Emit new_notification
                socketio.emit('new_notification', {
                    'type': 'FRIEND_REQUEST',
                    'sender_name': message.get('sender_name', 'Unknown'),
                    'message': f"{message.get('sender_name', 'Unknown')} sent you a friend request"
                }, room=f"user_{message['receiver_id']}")
                success = True

        elif msg_type == 'GROUP_INVITE':
            if write_group_invite(message):
                socketio.emit('new_notification', {
                    'type': 'GROUP_INVITE',
                    'sender_name': message.get('sender_name', 'Unknown'),
                    'message': f"{message.get('sender_name', 'Unknown')} invited you to {message.get('room_name', 'Chatroom')}"
                }, room=f"user_{message['receiver_id']}")
                success = True

        elif msg_type == 'FRIEND_ACCEPTED':
            if write_friend_accept(message):
                # Emit update_data to initiator (who is now friend)
                socketio.emit('update_data', {
                    'event': 'FRIEND_ACCEPTED',
                    'friend': {
                        'id': str(message['acceptor_id']),
                        'name': message.get('acceptor_name', 'Unknown'),
                        'avatarUrl': f"https://ui-avatars.com/api/?name={message.get('acceptor_name', 'Unknown')}",
                        'online': True
                    }
                }, room=f"user_{message['initiator_id']}")
                success = True

        elif msg_type == 'GROUP_JOINED':
             if write_group_join(message):
                 # Emit to the user who joined so they can update their room list
                 socketio.emit('added_to_room', {
                     'room_id': str(message['room_id'])
                 }, room=f"user_{message['user_id']}")
                 success = True

        else:
            # Default: Chat Message
            if write_message(message):
                # Chat message emit is handled by Publisher synchronously in current architecture
                success = True

        if success:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            print(f"Processed {msg_type if msg_type else 'CHAT_MESSAGE'}")
        else:
            print("Failed to process message (DB Error?)")
            # We don't verify 'success' if DB failed (write returns False), so we NACK.
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    except Exception as e:
        print("Error processing message:", e)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def start_consumer():
    print("Trying to connect to RabbitMQ...")
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST)
        )
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
        print("Consumer started and listening on:", QUEUE_NAME)
        channel.start_consuming()
    except Exception as e:
        print(f"Error starting consumer: {e}")

if __name__ == "__main__":
    start_consumer()
