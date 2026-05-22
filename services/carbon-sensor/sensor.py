import time
import json
import random
import os
import pika

broker_host = os.getenv('BROKER_HOST', 'localhost')

print("Analisador de Emissão de Carbono: Sensor iniciando...", flush=True)

connection = None
while not connection:
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=broker_host))
    except pika.exceptions.AMQPConnectionError:
        print("Aguardando o broker de mensagens iniciar...")
        time.sleep(3)

channel = connection.channel()

# Declarando a fila específica para emissão de carbono
channel.queue_declare(queue='carbon_emission_readings')

print("Sensor conectado com sucesso ao Middleware de Mensageria!")

while True:
    payload = {
        "sensor_id": "sensor-carbono-01",
        "carbon_emission": random.randint(300, 800), # Simulando emissão de CO2 entre 300 e 800 ppm
        "timestamp": time.time()
    }
    
    channel.basic_publish(
        exchange='',
        routing_key='carbon_emission_readings',
        body=json.dumps(payload)
    )
    print(f"[Sensor] Dado de emissão de carbono enviado: {payload['carbon_emission']} ppm")
    time.sleep(3) # 3 segundos de delay