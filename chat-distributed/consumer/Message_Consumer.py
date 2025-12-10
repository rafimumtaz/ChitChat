import pika
import json
import sys
import os

# Add the parent directory to sys.path to allow importing from sibling directories if needed
# But actually, we need to import from database_writer/db_writer.py
# Assuming the structure is:
# chat-distributed/
#   consumer/Message_Consumer.py
#   database_writer/db_writer.py

# We need to add chat-distributed/ to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database_writer.db_writer import write_message

# Konfigurasi RabbitMQ
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
QUEUE_NAME = 'chat_queue'

def callback(ch, method, properties, body):
    """
    Fungsi callback yang dijalankan saat pesan diterima.
    Pesan berasal dari publisher yang mengirim:
    sender_id, room_id, content
    """

    try:
        # Decode pesan JSON yang dikirim publisher
        message = json.loads(body)
        print("Received message from RabbitMQ:", message)

        # Simpan ke database
        # write_message dari db_writer.py
        if write_message(message):
             # Beri ACK untuk memberitahu RabbitMQ bahwa pesan telah diproses
            ch.basic_ack(delivery_tag=method.delivery_tag)
            print("Message Saved to Database & ACK Sent")
        else:
            print("Failed to save message to database. NACKing.")
            # Nack with requeue=True if it's a transient error, or False if permanent.
            # db_writer returns False on permanent failure or serious error.
            # If it's a temporary DB connection issue, db_writer might handle it or we might want to requeue.
            # Here we requeue.
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


    except Exception as e:
        print("Error processing message:", e)
        # Jika gagal → jangan ACK, supaya pesan tidak hilang
        # RabbitMQ akan mengirim ulang pesan nanti.
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def start_consumer():
    """
    Memulai consumer untuk mendengarkan pesan dari Queue.
    """

    print("Trying to connect to RabbitMQ...")

    try:
        # Membuat koneksi RabbitMQ
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST)
        )

        channel = connection.channel()

        # Pastikan queue ada (SAMA seperti di publisher)
        channel.queue_declare(queue=QUEUE_NAME, durable=True)

        # Agar consumer mengolah 1 pesan per waktu
        channel.basic_qos(prefetch_count=1)

        # Mendaftarkan callback
        channel.basic_consume(
            queue=QUEUE_NAME,
            on_message_callback=callback
        )

        print("Consumer started and listening on:", QUEUE_NAME)
        print("Waiting for messages...\n")

        channel.start_consuming()
    except Exception as e:
        print(f"Error starting consumer: {e}")

if __name__ == "__main__":
    start_consumer()
