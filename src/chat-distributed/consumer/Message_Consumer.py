import pika
import json
from db_writer import save_to_db   # pastikan file db_writer.py ada 1 folder dengan file ini

# Konfigurasi RabbitMQ
RABBITMQ_HOST = 'localhost'
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
        # save_to_db harus menerima dictionary yang berisi
        # sender_id, room_id, content
        save_to_db(message)

        # Beri ACK untuk memberitahu RabbitMQ bahwa pesan telah diproses
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print("Message Saved to Database & ACK Sent")

    except Exception as e:
        print("Error processing message:", e)
        # Jika gagal → jangan ACK, supaya pesan tidak hilang
        # RabbitMQ akan mengirim ulang pesan nanti.

def start_consumer():
    """
    Memulai consumer untuk mendengarkan pesan dari Queue.
    """

    print("Trying to connect to RabbitMQ...")

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

if __name__ == "__main__":
    start_consumer()
