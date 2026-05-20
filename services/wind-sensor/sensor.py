import time
import json
import random
import os
import pika
import uuid
from middleware.logger import log_mensagem 

broker_host = os.getenv('BROKER_HOST', 'localhost')
print("Analisador de Velocidade de Vento: Sensor iniciando...", flush=True)

connection = None
while not connection:
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=broker_host))
    except pika.exceptions.AMQPConnectionError:
        time.sleep(3)

channel = connection.channel()
channel.queue_declare(queue='humidity_readings')

while True:
    velocidade_vento = random.randint(30, 85)
    id_customizado = f"b-{uuid.uuid4()}"
    
    c_id = log_mensagem(
        servico="wind-sensor", 
        acao="ENVIAR_DADO", 
        message="Capturando velocidade do vento",
        correlation_id=id_customizado
    )
    
    payload = {
        "correlation_id": c_id,
        "sensor_id": "b-sensor-vento-anemometro-01",
        "tipo_sensor": "wind",
        "wind_speed": velocidade_vento,
        "timestamp": time.time()
    }
    
    channel.basic_publish(exchange='', routing_key='humidity_readings', body=json.dumps(payload))
    print(f"🍃 [VENTO] Enviado: {velocidade_vento} km/h | ID: {c_id[:10]}...", flush=True)
    time.sleep(3)