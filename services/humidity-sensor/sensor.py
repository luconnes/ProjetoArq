import time
import json
import random
import os
import pika
import uuid
from middleware.logger import log_mensagem 

broker_host = os.getenv('BROKER_HOST', 'localhost')
print("Analisador de Umidade: Sensor iniciando...", flush=True)

connection = None
while not connection:
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=broker_host))
    except pika.exceptions.AMQPConnectionError:
        time.sleep(3)

channel = connection.channel()
channel.queue_declare(queue='humidity_readings')

while True:
    umidade_atual = random.randint(30, 85)
    id_customizado = f"a-{uuid.uuid4()}"
  
    c_id = log_mensagem(
        servico="humidity-sensor", 
        acao="ENVIAR_DADO", 
        message="Capturando umidade do ar",
        correlation_id=id_customizado
    )
    
    payload = {
        "correlation_id": c_id,
        "sensor_id": "a-sensor-umidade-sala-01",
        "tipo_sensor": "humidity",
        "humidity": umidade_atual,
        "timestamp": time.time()
    }
    
    channel.basic_publish(exchange='', routing_key='humidity_readings', body=json.dumps(payload))
    print(f"💧 [UMIDADE] Enviado: {umidade_atual}% | ID: {c_id[:10]}...", flush=True)
    time.sleep(3)