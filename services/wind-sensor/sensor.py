import time
import json
import random
import os
import pika


broker_host = os.getenv('BROKER_HOST', 'localhost')

print("Analisador de Velocidade de Vento: Sensor iniciando...")

 
connection = None
while not connection:
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=broker_host))
    except pika.exceptions.AMQPConnectionError:
        print("Aguardando o broker de mensagens iniciar...")
        time.sleep(3)

channel = connection.channel()
channel.queue_declare(queue='wind-velocity_readings')

print("Sensor conectado com sucesso ao Middleware de Mensageria!")


while True:
    payload = {
        "sensor_id": "sensor-sala-01",
        "wind-velocity": random.randint(30, 85), 
        "timestamp": time.time()
    }
    
    
    channel.basic_publish(
        exchange='',
        routing_key='wind-velocity_readings',
        body=json.dumps(payload)
    )
    print(f"[Sensor] Dado de velocidade do vento enviado: {payload['wind-velocity']}m/s")
    time.sleep(3) # 3 segundos de delay