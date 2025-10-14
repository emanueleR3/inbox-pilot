import json
import aio_pika
from src.utils.logger import log_info, log_error
import os
from dotenv import load_dotenv

load_dotenv()

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
QUEUE_NAME = os.getenv("IMAP_QUEUE_NAME", "emails_queue")

class RabbitMQPublisher:
    def __init__(self):
        self.connection = None
        self.channel = None

    async def connect(self):
        try:
            self.connection = await aio_pika.connect_robust(RABBITMQ_URL)
            self.channel = await self.connection.channel()
            await self.channel.declare_queue(QUEUE_NAME, durable=True)
            log_info("✅ Connesso a RabbitMQ e coda dichiarata")
        except Exception as e:
            log_error(f"Errore di connessione a RabbitMQ: {e}")
            raise

    async def publish_message(self, message: dict):
        if not self.connection or self.connection.is_closed:
            await self.connect()

        try:
            msg_body = json.dumps(message).encode()
            await self.channel.default_exchange.publish(
                aio_pika.Message(
                    body=msg_body,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=QUEUE_NAME,
            )
            log_info(f"📨 Messaggio pubblicato su RabbitMQ → {QUEUE_NAME}")

        except Exception as e:
            log_error(f"Errore pubblicando su RabbitMQ: {e}")