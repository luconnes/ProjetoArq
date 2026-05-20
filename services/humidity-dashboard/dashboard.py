import threading
import json
import os
import time
import pika
from flask import Flask, jsonify

# Importa o logger e a nova função de validação de segurança do seu middleware
from middleware.logger import log_mensagem, validar_json_payload

app = Flask(__name__)
broker_host = os.getenv('BROKER_HOST', 'localhost')

# Estado inicial da leitura na memória temporária
ultima_leitura = {"status": "Sem dados recebidos ainda", "correlation_id": None}

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
        
        # 🛡️ SEGURANÇA: O middleware valida se o JSON recebido segue o contrato estrito
        dados_validados = validar_json_payload(body)
        
        if dados_validados is None:
            # Se o JSON for malicioso, corrompido ou inválido, bloqueia e gera alerta
            log_mensagem(
                servico="humidity-dashboard",
                acao="PROCESSAR_DADO",
                message="REJEITADO: JSON recebido está corrompido ou fora do formato obrigatório!",
                level="SECURITY_ALERT"
            )
            return  # Aborta o processamento para proteger o dashboard

        # Se passou na validação, atualiza o estado e processa normalmente
        ultima_leitura = dados_validados
        c_id = ultima_leitura.get("correlation_id")
        
        # Registra o log de sucesso com o mesmo ID de correlação
        log_mensagem(
            servico="humidity-dashboard",
            acao="PROCESSAR_DADO",
            message=f"Umidade processada e armazenada: {ultima_leitura['humidity']}%",
            correlation_id=c_id,
            level="INFO"
        )

    #callback de velocidade do vento
    def callbackWind(ch, method, prpoerties, body) :
        global ultima_leitura_vento
        ultima_leitura_vento = json.loads(body)
        print(f"[Dashboard] Processando velocidade do vento recebida: {ultima_leitura_vento}m/s")


    channel.basic_consume(queue='humidity_readings', on_message_callback=callback, auto_ack=True)
<<<<<<< Updated upstream
    channel.basic_consume(queue='wind-velocity_readings', on_message_callback=callbackWind, auto_ack=True)
    print("Dashboard pronto e escutando a fila de eventos...")
=======
    print("Dashboard pronto e escutando a fila de eventos com validação de segurança...", flush=True)
>>>>>>> Stashed changes
    channel.start_consuming()

@app.route('/api/humidity/current', methods=['GET'])
def get_humidity():
    # A API síncrona entrega o JSON completo e validado
    return jsonify(ultima_leitura), 200
def get_wind():
    return jsonify(ultima_leitura_vento), 200

if __name__ == '__main__':
    threading.Thread(target=iniciar_consumidor_fila, daemon=True).start()
    app.run(host='0.0.0.0', port=8080)