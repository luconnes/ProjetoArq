import threading
import json
import os
import time
import pika
from flask import Flask, jsonify

app = Flask(__name__)
broker_host = os.getenv('BROKER_HOST', 'localhost')

# Memória temporária para guardar a última leitura recebida
ultima_leitura = {"status": "Sem dados recebidos ainda"}

# --- PARTE ASSÍNCRONA: Consumir dados da fila ---
def iniciar_consumidor_fila():
    connection = None
    while not connection:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=broker_host))
        except pika.exceptions.AMQPConnectionError:
            time.sleep(3)

    channel = connection.channel()
    channel.queue_declare(queue='humidity_readings')

    def callback(ch, method, properties, body):
        global ultima_leitura
        ultima_leitura = json.loads(body)
        print(f"[Dashboard] Processando umidade recebida: {ultima_leitura['humidity']}%")

    channel.basic_consume(queue='humidity_readings', on_message_callback=callback, auto_ack=True)
    print("Dashboard pronto e escutando a fila de eventos...")
    channel.start_consuming()

# --- PARTE SÍNCRONA: API REST para consultas ---
@app.route('/api/humidity/current', methods=['GET'])
def get_humidity():
    # Retorna o dado síncronamente quando requisitado 
    return jsonify(ultima_leitura), 200

if __name__ == '__main__':
    # Inicializa a escuta da fila em segundo plano (background thread)
    threading.Thread(target=iniciar_consumidor_fila, daemon=True).start()
    
    # Inicializa o servidor web da API REST na porta 8080
    app.run(host='0.0.0.0', port=8080)