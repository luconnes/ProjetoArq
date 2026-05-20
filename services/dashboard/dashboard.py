import threading
import json
import os
import time
import pika
from flask import Flask, jsonify, render_template_string
from middleware.logger import log_mensagem, validar_json_payload

app = Flask(__name__)
broker_host = os.getenv('BROKER_HOST', 'localhost')
dados_sensores = {}

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
        global dados_sensores
        dados_validados = validar_json_payload(body)
        
        if dados_validados is None:
            log_mensagem(
                servico="dashboard",
                acao="PROCESSAR_DADO",
                message="REJEITADO: Payload inválido!",
                level="SECURITY_ALERT"
            )
            return

        tipo = dados_validados.get("tipo_sensor")
        s_id = dados_validados.get("sensor_id")
        c_id = dados_validados.get("correlation_id")
        
        dados_sensores[tipo] = dados_validados
        
        print(f"\n🟩 [DADO RECEBIDO] ID: {s_id} | Tipo: {tipo.upper()}", flush=True)
        print(f"   ↳ Valores: { {k:v for k,v in dados_validados.items() if k not in ['correlation_id','sensor_id','tipo_sensor','timestamp']} }", flush=True)
        print(f"   ↳ ID Correlação: {c_id}\n", flush=True)

    channel.basic_consume(queue='humidity_readings', on_message_callback=callback, auto_ack=True)
    channel.start_consuming()

HTML_PAGINA = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Painel de Monitoramento Multissensor</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; background: #f4f6f9; margin: 0; padding: 20px; color: #333; }
        h1 { text-align: center; color: #2c3e50; }
        .container { display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; margin-top: 30px; }
        .card { background: white; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); padding: 20px; width: 280px; border-top: 5px solid #3498db; }
        .card.wind { border-top-color: #2ecc71; }
        .card h2 { margin-top: 0; color: #34495e; text-transform: capitalize; }
        .vazio { text-align: center; color: #7f8c8d; font-style: italic; }
        .dado { font-size: 24px; font-weight: bold; color: #2c3e50; margin: 15px 0; }
        .meta { font-size: 11px; color: #95a5a6; word-break: break-all; }
    </style>
    <script>
        setInterval(async () => {
            const resposta = await fetch('/api/sensors/current');
            const dados = await resposta.json();
            const container = document.getElementById('cards-container');
            if (Object.keys(dados).length === 0) return;
            container.innerHTML = '';
            for (const [tipo, payload] of Object.entries(dados)) {
                const valor = payload.humidity !== undefined ? payload.humidity + '%' : payload.wind_speed + ' km/h';
                const card = document.createElement('div');
                card.className = `card ${tipo}`;
                card.innerHTML = `
                    <h2>Sensor: ${tipo}</h2>
                    <p style="font-size:12px; color:#7f8c8d; margin:0;">ID: ${payload.sensor_id}</p>
                    <div class="dado">${valor}</div>
                    <div class="meta"><p><strong>ID Correlação:</strong><br>${payload.correlation_id}</p></div>
                `;
                container.appendChild(card);
            }
        }, 1500);
    </script>
</head>
<body>
    <h1>📊 Painel Central de Sensores Distribuídos</h1>
    <div class="container" id="cards-container">
        <p class="vazio">Aguardando sinais dos sensores na fila do RabbitMQ...</p>
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def home(): return render_template_string(HTML_PAGINA)

@app.route('/api/sensors/current', methods=['GET'])
def get_all_sensors(): return jsonify(dados_sensores), 200

if __name__ == '__main__':
    threading.Thread(target=iniciar_consumidor_fila, daemon=True).start()
    app.run(host='0.0.0.0', port=8080)