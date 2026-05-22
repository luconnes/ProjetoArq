import time
import json
import random
import os
import pika
import uuid
from middleware.logger import log_mensagem 

broker_host = os.getenv('BROKER_HOST', 'localhost')
print("Analisador de Luminosidade: Sensor iniciando...", flush=True)

connection = None
while not connection:
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=broker_host))
    except pika.exceptions.AMQPConnectionError:
        time.sleep(3)

channel = connection.channel()
channel.queue_declare(queue='humidity_readings')

while True:
    luminosidade_atual = random.randint(0, 1000)
    id_customizado = f"c-{uuid.uuid4()}"
    
    c_id = log_mensagem(
        servico="luminosity-sensor", 
        acao="ENVIAR_DADO", 
        message="Capturando luminosidade do ambiente",
        correlation_id=id_customizado
    )
    
    payload = {
        "correlation_id": c_id,
        "sensor_id": "c-sensor-luz-01",
        "tipo_sensor": "luminosity",
        "luminosity": luminosidade_atual,
        "timestamp": time.time()
    }
    
    channel.basic_publish(exchange='', routing_key='humidity_readings', body=json.dumps(payload))
    print(f"💡 [LUZ] Enviado: {luminosidade_atual} lux | ID: {c_id[:10]}...", flush=True)
    time.sleep(3)