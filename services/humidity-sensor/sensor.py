import time
import json
import random
import os
import pika

from middleware.logger import log_mensagem 

broker_host = os.getenv('BROKER_HOST', 'localhost')

print("Analisador de Umidade: Sensor iniciando...", flush=True)

connection = None
while not connection:
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=broker_host))
    except pika.exceptions.AMQPConnectionError:
        print("Aguardando o broker de mensagens iniciar...", flush=True)
        time.sleep(3)

channel = connection.channel()
channel.queue_declare(queue='humidity_readings')

print("Sensor conectado com sucesso ao Middleware de Mensageria!", flush=True)

while True:
    umidade_atual = random.randint(30, 85)
    
    
    c_id = log_mensagem(
        servico="humidity-sensor", 
        acao="ENVIAR_DADO", 
        message=f"Capturando umidade do ar"
    )
    
   
    payload = {
        "correlation_id": c_id,
        "sensor_id": "sensor-sala-01",
        "humidity": umidade_atual,
        "timestamp": time.time()
    }
    
    channel.basic_publish(
        exchange='', 
        routing_key='humidity_readings', 
        body=json.dumps(payload)
    )
    
    time.sleep(3)  # Delay de 3 segundos
