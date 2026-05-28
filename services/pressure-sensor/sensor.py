import time
import json
import random
import os
import pika
import uuid
from middleware.logger import log_mensagem 

broker_host = os.getenv('BROKER_HOST', 'localhost')
print("Analisador de Pressão Atmosférica: Sensor iniciando...", flush=True)

def conectar_com_retry():
    tentativas = 0
    max_tentativas = 5
    delay = 2 
    
    while tentativas < max_tentativas:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=broker_host))
            print("Sensor conectado com sucesso ao Middleware de Mensageria!", flush=True)
            return connection
        except pika.exceptions.AMQPConnectionError:
            tentativas += 1
            print(f"Falha ao conectar no RabbitMQ. Tentativa {tentativas}/{max_tentativas}. Tentando novamente em {delay} segundos...", flush=True)
            time.sleep(delay)
            delay *= 2
            
    raise Exception("Falha crítica: Não foi possível conectar ao broker após várias tentativas.")

connection = conectar_com_retry()
channel = connection.channel()
channel.queue_declare(queue='pressure_readings')


pressao_atual = 1013.0 

while True:
    try:
        
        variacao = random.uniform(-2.0, 2.0)
        pressao_atual = round(pressao_atual + variacao, 2)
        id_customizado = f"p-{uuid.uuid4()}"
        
        c_id = log_mensagem(
            servico="pressure-sensor", 
            acao="ENVIAR_DADO", 
            message=f"Capturando pressão atmosférica: {pressao_atual} hPa",
            correlation_id=id_customizado
        )
        
        payload = {
            "correlation_id": c_id,
            "sensor_id": "sensor-pressao-01",
            "pressure": pressao_atual, 
            "timestamp": time.time()
        }
        
        channel.basic_publish(
            exchange='',
            routing_key='pressure_readings',
            body=json.dumps(payload)
        )
        time.sleep(3) 
        
    except pika.exceptions.AMQPConnectionError:
        print("Conexão perdida! Tentando reconectar...", flush=True)
       
        connection = conectar_com_retry()
        channel = connection.channel()