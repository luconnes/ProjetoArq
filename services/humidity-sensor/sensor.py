import time
import json
import random
import os
import pika

# Pega o host configurado no docker-compose
broker_host = os.getenv('BROKER_HOST', 'localhost')

print("Analisador de Umidade: Sensor iniciando...")

# Loop para tentar conectar na fila caso o RabbitMQ demore a subir (Resiliência básica!)
connection = None
while not connection:
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=broker_host))
    except pika.exceptions.AMQPConnectionError:
        print("Aguardando o broker de mensagens iniciar...")
        time.sleep(3)

channel = connection.channel()
channel.queue_declare(queue='humidity_readings')

print("Sensor conectado com sucesso ao Middleware de Mensageria!")

# Simula leituras constantes do sensor IoT
while True:
    payload = {
        "sensor_id": "sensor-sala-01",
        "humidity": random.randint(30, 85), # Simula porcentagem de umidade
        "timestamp": time.time()
    }
    
    # Publica a mensagem na fila de forma assíncrona
    channel.basic_publish(
        exchange='',
        routing_key='humidity_readings',
        body=json.dumps(payload)
    )
    print(f"[Sensor] Dado de umidade enviado: {payload['humidity']}%")
    time.sleep(3) # Coleta a cada 3 segundos