import threading
import json
import os
import time
import pika
from flask import Flask, jsonify

app = Flask(__name__)
broker_host = os.getenv('BROKER_HOST', 'localhost')

#teste teste teste
ultima_leitura = {"status": "Sem dados recebidos ainda"}


def iniciar_consumidor_fila():
    connection = None
    while not connection:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=broker_host))
        except pika.exceptions.AMQPConnectionError:
            time.sleep(3)

    channel = connection.channel()
    channel.queue_declare(queue='humidity_readings')
    #queue de velocidade do vento
    channel.queue_declare(queue='wind-velocity_readings')

    def callback(ch, method, properties, body):
        global ultima_leitura
        ultima_leitura = json.loads(body)
        print(f"[Dashboard] Processando umidade recebida: {ultima_leitura['humidity']}%")

    #callback de velocidade do vento
    def callbackWind(ch, method, prpoerties, body) :
        global ultima_leitura_vento
        ultima_leitura_vento = json.loads(body)
        print(f"[Dashboard] Processando velocidade do vento recebida: {ultima_leitura_vento}m/s")


    channel.basic_consume(queue='humidity_readings', on_message_callback=callback, auto_ack=True)
    channel.basic_consume(queue='wind-velocity_readings', on_message_callback=callbackWind, auto_ack=True)
    print("Dashboard pronto e escutando a fila de eventos...")
    channel.start_consuming()


@app.route('/api/humidity/current', methods=['GET'])
def get_humidity():
    
    return jsonify(ultima_leitura), 200
def get_wind():
    return jsonify(ultima_leitura_vento), 200

if __name__ == '__main__':
    
    threading.Thread(target=iniciar_consumidor_fila, daemon=True).start()
    
   
    app.run(host='0.0.0.0', port=8080)