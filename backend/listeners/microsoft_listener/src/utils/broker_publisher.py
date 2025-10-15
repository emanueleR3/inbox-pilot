import aio_pika
import json
import os
from dotenv import load_dotenv

load_dotenv()

RABBITMQ_URL = os.getenv("RABBITMQ_URL")
QUEUE_NAME = os.getenv("IMAP_QUEUE_NAME", "emails_queue")

async def publish_to_broker(messages):
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    await channel.declare_queue("emails_queue", durable=True)

    for msg in messages:
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(msg).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=QUEUE_NAME,
        )

    await connection.close()