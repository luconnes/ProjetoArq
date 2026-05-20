import time
import json
import random
import os
import pika

broker_host = os.getenv('BROKER_HOST', 'localhost')

print("Analisador de Temperatura: Sensor iniciando...")

connection = None
while not connection:
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=broker_host))
    except pika.exceptions.AMQPConnectionError:
        print("Aguardando o broker de mensagens iniciar...")
        time.sleep(3)

channel = connection.channel()
# Declarando a fila específica para temperatura
channel.queue_declare(queue='temperature_readings')

print("Sensor conectado com sucesso ao Middleware de Mensageria!")

while True:
    payload = {
        "sensor_id": "sensor-sala-01",
        "temperature": random.randint(15, 45), # Simulando temperatura entre 15°C e 45°C
        "timestamp": time.time()
    }
    
    channel.basic_publish(
        exchange='',
        routing_key='temperature_readings',
        body=json.dumps(payload)
    )
    print(f"[Sensor] Dado de temperatura enviado: {payload['temperature']}°C")
    time.sleep(3) # 3 segundos de delay