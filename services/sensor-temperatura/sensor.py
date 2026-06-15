import time
import json
import random
import os
import pika
import uuid
from middleware.logger import log_mensagem 

broker_host = os.getenv('BROKER_HOST', 'localhost')
print("Analisador de Temperatura: Sensor iniciando...", flush=True)

connection = None
while not connection:
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=broker_host))
    except pika.exceptions.AMQPConnectionError:
        time.sleep(3)

channel = connection.channel()
channel.queue_declare(queue='humidity_readings')

while True:
    temperatura_atual = random.randint(15, 45)
    id_customizado = f"e-{uuid.uuid4()}"
    
    c_id = log_mensagem(
        servico="sensor-temperatura", 
        acao="ENVIAR_DADO", 
        message="Capturando temperatura ambiente",
        correlation_id=id_customizado
    )
    
    payload = {
        "correlation_id": c_id,
        "sensor_id": "e-sensor-temperatura-01",
        "tipo_sensor": "temperature",
        "temperature": temperatura_atual,
        "timestamp": time.time()
    }
    
    channel.basic_publish(exchange='', routing_key='humidity_readings', body=json.dumps(payload))
    print(f"🌡️ [TEMPERATURA] Enviado: {temperatura_atual}°C | ID: {c_id[:10]}...", flush=True)
    time.sleep(3)