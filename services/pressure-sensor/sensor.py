import time
import json
import random
import os
import pika

broker_host = os.getenv('BROKER_HOST', 'localhost')

print("Analisador de Pressão Atmosférica: Sensor iniciando...", flush=True)

connection = None
while not connection:
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=broker_host))
    except pika.exceptions.AMQPConnectionError:
        print("Aguardando o broker de mensagens iniciar...")
        time.sleep(3)

channel = connection.channel()

channel.queue_declare(queue='pressure_readings')

print("Sensor conectado com sucesso ao Middleware de Mensageria!")

while True:
    
    payload = {
        "sensor_id": "sensor-pressao-01",
        "pressure": random.randint(900, 1100), 
        "timestamp": time.time()
    }
    
    channel.basic_publish(
        exchange='',
        routing_key='pressure_readings',
        body=json.dumps(payload)
    )
    print(f"[Sensor] Dado de pressão enviado: {payload['pressure']} hPa")
    time.sleep(3) 