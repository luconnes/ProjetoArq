import time
import json
import random
import os
import pika

from middleware.logger import log_mensagem 

broker_host = os.getenv('BROKER_HOST', 'localhost')

print("Analisador de Luminosidade: Sensor iniciando...", flush=True)

connection = None
while not connection:
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=broker_host))
    except pika.exceptions.AMQPConnectionError:
        print("Aguardando o broker de mensagens iniciar...", flush=True)
        time.sleep(3)

channel = connection.channel()
channel.queue_declare(queue='luminosity_readings')

print("Sensor conectado com sucesso ao Middleware de Mensageria!", flush=True)

while True:
    luminosidade_atual = random.randint(0, 1000)
    
    c_id = log_mensagem(
        servico="luminosity-sensor", 
        acao="ENVIAR_DADO", 
        message="Capturando luminosidade do ambiente"
    )
    
    payload = {
        "correlation_id": c_id,
        "sensor_id": "sensor-luz-01",
        "luminosity": luminosidade_atual,
        "timestamp": time.time()
    }
    
    channel.basic_publish(
        exchange='', 
        routing_key='luminosity_readings', 
        body=json.dumps(payload)
    )
    
    time.sleep(3)