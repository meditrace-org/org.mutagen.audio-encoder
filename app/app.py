from faster_whisper import WhisperModel
from io import BytesIO
import numpy as np
import json
import base64
import torch

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic
from common.config import settings
from common.clients.amqp import Session
import app.monitoring as monitoring
from transformers import AutoModel, pipeline


def deserialize(encoded_string):
    return base64.b64decode(encoded_string)


session = Session()
session.set_connection_params(
    host=str(settings.rabbitmq.host),
    port=settings.rabbitmq.port,
    virtual_host=settings.rabbitmq.virtual_host,
    username=settings.rabbitmq.username,
    password=settings.rabbitmq.password,
)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model = WhisperModel(settings.encoder.voice_encoder, device="cuda" if torch.cuda.is_available() else "cpu")
clip = AutoModel.from_pretrained(settings.encoder.encoder, trust_remote_code=True).to(device)
opus = pipeline("translation", model="Helsinki-NLP/opus-mt-ru-en", device=device)


@session.on_message
def listen(channel: BlockingChannel, method: Basic.Deliver,
           properties: pika.BasicProperties, body: bytes):
    monitoring.timer.start('preprocessing')

    value = json.loads(body.decode().replace("'", '"'))
    id = value['uuid']
    chunk = value['serialized_chunk']
    chunk = deserialize(chunk)

    monitoring.processing_duration_seconds.labels('preprocessing') \
        .observe(monitoring.timer.get('preprocessing'))
    monitoring.timer.start('inference')

    segments, info = model.transcribe(BytesIO(chunk),
                                      task="transcribe",
                                      language="ru")

    text = ""
    for segment in segments:
        text += segment.text

    text_en = opus(text)[0]["translation_text"]

    emb = clip.encode_text(text_en).astype(np.float16)
    print(text)
    monitoring.processing_duration_seconds.labels('inference') \
        .observe(monitoring.timer.get('inference'))
    monitoring.timer.start('publishing')

    #print(emb.tolist())
    send = {
        "uuid": id,
        "model": settings.encoder.voice_encoder,
        "text": text,
        "encoded_chunk": emb.tolist()
    }
    session.publish(
        exchange="",
        routing_key=settings.rabbitmq.audio_queue,
        body=json.dumps(send),
        properties=pika.BasicProperties(
            content_type='application/json'
        )
    )
    channel.basic_ack(delivery_tag=method.delivery_tag)

    monitoring.processing_duration_seconds.labels('publishing')\
        .observe(monitoring.timer.get('publishing'))
    monitoring.messages_processed_total.inc()


def main():
    session.start_consuming(
        settings.rabbitmq.audio_chunks_queue,
        prefetch_count=settings.rabbitmq.prefetch_count
    )
