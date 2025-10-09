import aio_pika
import os
from dotenv import load_dotenv

load_dotenv()

# TODO configurare RABBITMQ
RABBITMQ_URL = os.getenv("RABBITMQ_URL")

async def get_connection():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)  # max 10 messaggi non elaborati per worker
    queue = await channel.declare_queue("emails_queue", durable=True)
    return connection, channel, queue