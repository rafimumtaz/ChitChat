import json
from flask import Flask, request, jsonify
import pika
import mysql.connector 

app = Flask(__name__)

# Konfigurasi RabbitMQ 
RABBITMQ_HOST = 'localhost'
RABBITMQ_QUEUE = 'chat_queue'

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

    # Panggil fungsi publisher
    if publish_message(data):
        return jsonify({
            "status": "accepted", 
            "message": "Message successfully handed over to RabbitMQ",
            "next_step": "Waiting for Consumer Service to process and store in DB"
        }), 202
    else:
        return jsonify({"status": "error", "message": "Message Broker is unavailable. Try again later."}), 503

if __name__ == '__main__':
    print(" === Application Server (Message Publisher) Started ===")
    app.run(debug=True, port=5000)