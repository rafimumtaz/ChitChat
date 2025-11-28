"""
RabbitMQ Message Broker Setup Service
------------------------------------
Tugas file ini:
1. Membuat exchange (chat_exchange)
2. Membuat queue (chat_queue)
3. Melakukan binding routing_key
4. Menjamin durability dan persistence
5. Menyediakan fungsi health-check
"""

import pika

RABBITMQ_HOST = "localhost"
EXCHANGE_NAME = "chat_exchange"
QUEUE_NAME = "chat_queue"
ROUTING_KEY = "chat.message"

def setup_broker():
    print("\n================================")
    print("   RabbitMQ Broker Initializing ")
    print("================================\n")

    try:
        # 1. Connect ke RabbitMQ Server
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST)
        )
        channel = connection.channel()

        # 2. Membuat exchange tipe direct
        channel.exchange_declare(
            exchange=EXCHANGE_NAME,
            exchange_type="direct",
            durable=True
        )
        print(f"[+] Exchange '{EXCHANGE_NAME}' created (durable=True)")

        # 3. Membuat queue
        channel.queue_declare(
            queue=QUEUE_NAME,
            durable=True
        )
        print(f"[+] Queue '{QUEUE_NAME}' created (durable=True)")

        # 4. Binding queue → exchange
        channel.queue_bind(
            exchange=EXCHANGE_NAME,
            queue=QUEUE_NAME,
            routing_key=ROUTING_KEY
        )
        print(f"[+] Queue bound to Exchange using routing key '{ROUTING_KEY}'")

        connection.close()
        print("\n[✓] RabbitMQ Broker setup completed successfully.\n")

    except Exception as e:
        print("\n[❌] RabbitMQ Broker setup FAILED:", e, "\n")


def health_check():
    """
    Mengecek apakah RabbitMQ sedang berjalan.
    """
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST)
        )
        connection.close()
        return True
    except:
        return False


if __name__ == "__main__":
    setup_broker()

    if health_check():
        print("[✓] RabbitMQ is UP & reachable.")
    else:
        print("[❌] RabbitMQ is DOWN or unreachable.")
