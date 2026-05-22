import time
import json
import random
import os
import pika
import uuid
from middleware.logger import log_mensagem 

broker_host = os.getenv('BROKER_HOST', 'localhost')
print("Analisador de Pressão Atmosférica: Sensor iniciando...", flush=True)

connection = None
while not connection:
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=broker_host))
    except pika.exceptions.AMQPConnectionError:
        time.sleep(3)

channel = connection.channel()
channel.queue_declare(queue='humidity_readings')

while True:
    pressao_atual = random.randint(900, 1100)
    id_customizado = f"d-{uuid.uuid4()}"
    
    c_id = log_mensagem(
        servico="pressure-sensor", 
        acao="ENVIAR_DADO", 
        message="Capturando pressao atmosferica",
        correlation_id=id_customizado
    )
    
    payload = {
        "correlation_id": c_id,
        "sensor_id": "d-sensor-pressao-01",
        "tipo_sensor": "pressure",
        "pressure": pressao_atual,
        "timestamp": time.time()
    }
    
    channel.basic_publish(exchange='', routing_key='humidity_readings', body=json.dumps(payload))
    print(f"🎈 [PRESSÃO] Enviado: {pressao_atual} hPa | ID: {c_id[:10]}...", flush=True)
    time.sleep(3)