import json
import aio_pika
import os
from src.utils.logger import log_info, log_error
from dotenv import load_dotenv

load_dotenv()

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
QUEUE_NAME = os.getenv("QUEUE_NAME", "emails_queue")

class RabbitMQPublisher:
    def __init__(self):
        self.connection = None
        self.channel = None

    async def connect(self):
        if self.connection and not self.connection.is_closed:
            return

        try:
            self.connection = await aio_pika.connect_robust(RABBITMQ_URL)
            self.channel = await self.connection.channel()
            await self.channel.declare_queue(QUEUE_NAME, durable=True)
            log_info(f"✅ Connesso a RabbitMQ, coda '{QUEUE_NAME}' pronta")
        except Exception as e:
            log_error(f"Errore connessione RabbitMQ: {e}")
            raise

    async def publish_message(self, message: dict):
        try:
            if not self.channel or self.channel.is_closed:
                await self.connect()

            body = json.dumps(message).encode()
            await self.channel.default_exchange.publish(
                aio_pika.Message(
                    body=body,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=QUEUE_NAME
            )
            log_info(f"📨 Pubblicata mail su RabbitMQ → {QUEUE_NAME}")
        except Exception as e:
            log_error(f"Errore pubblicazione su RabbitMQ: {e}")