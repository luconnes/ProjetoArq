import os
import sys
import time
import threading
import json

try:
    import fastapi
    import uvicorn
except ImportError:
    print("🔄 [DASHBOARD] Instalando dependencias necessarias (fastapi, uvicorn)...", flush=True)
    os.system(f"{sys.executable} -m pip install fastapi uvicorn")
    import fastapi
    import uvicorn

import pika
from flask import Flask, jsonify, render_template_string
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from middleware.logger import log_mensagem, validar_json_payload

broker_host = os.getenv('BROKER_HOST', 'localhost')
dados_sensores = {}
status_sincrono_sensores = {
    "humidity": {"status": "Inativo", "ultima_verificacao": "-"},
    "wind": {"status": "Inativo", "ultima_verificacao": "-"},
    "luminosity": {"status": "Inativo", "ultima_verificacao": "-"},
    "pressure": {"status": "Inativo", "ultima_verificacao": "-"},
    "temperature": {"status": "Inativo", "ultima_verificacao": "-"}
}
TIMEOUT_SENSOR_ONLINE = 7

USUARIOS_PERMISSOES = {
    "token-admin-123": {"nome": "Lucas (Professor)", "role": "admin"},
    "token-usuario-456": {"nome": "Integrante-02", "role": "user"}
}

api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

def obter_usuario_atual(token: str = Depends(api_key_header)):
    if not token or token not in USUARIOS_PERMISSOES:
        log_mensagem(
            servico="dashboard-security",
            acao="AUTENTICACAO",
            message="Tentativa de acesso negada: Token inválido ou ausente.",
            level="SECURITY_ALERT"
        )
        raise HTTPException(
            status_code=401, 
            detail="Não autorizado: Token X-API-KEY inválido ou ausente."
        )
    return USUARIOS_PERMISSOES[token]

def verificar_papel_admin(usuario=Depends(obter_usuario_atual)):
    if usuario["role"] != "admin":
        log_mensagem(
            servico="dashboard-security",
            acao="AUTORIZACAO",
            message=f"Usuário '{usuario['nome']}' com papel '{usuario['role']}' tentou acessar recurso de ADMIN.",
            level="SECURITY_ALERT"
        )
        raise HTTPException(
            status_code=403, 
            detail="Proibido: Apenas usuários com o papel 'admin' podem acessar este recurso."
        )
    return usuario

app_fastapi = FastAPI(
    title="API Síncrona Segura de Verificação de Sensores",
    description="Endpoints REST protegidos por autenticação de Token e autorização baseada em papéis (RBAC)."
)

@app_fastapi.get("/api/sensors/status")
def get_sensors_status_sincrono(usuario=Depends(verificar_papel_admin)):
    global status_sincrono_sensores, dados_sensores
    tempo_atual = time.time()
    for tipo, payload in dados_sensores.items():
        if tempo_atual - payload.get("timestamp", 0) > TIMEOUT_SENSOR_ONLINE:
            status_sincrono_sensores[tipo]["status"] = "Desconectado/Inativo"
            
    log_mensagem(
        servico="dashboard-fastapi",
        acao="REQUISICAO_SINCRONA",
        message=f"Usuário administrador '{usuario['nome']}' consultou o status geral."
    )
    return status_sincrono_sensores

@app_fastapi.get("/api/sensors/status/{tipo_sensor}")
def get_single_sensor_status_sincrono(tipo_sensor: str, usuario=Depends(obter_usuario_atual)):
    global status_sincrono_sensores, dados_sensores
    tipo = tipo_sensor.lower()
    
    if tipo not in status_sincrono_sensores:
        raise HTTPException(status_code=404, detail=f"Sensor '{tipo}' não existe no escopo.")
        
    tempo_atual = time.time()
    if tipo in dados_sensores:
        if tempo_atual - dados_sensores[tipo].get("timestamp", 0) > TIMEOUT_SENSOR_ONLINE:
            status_sincrono_sensores[tipo]["status"] = "Desconectado/Inativo"
            
    log_mensagem(
        servico="dashboard-fastapi",
        acao="REQUISICAO_SINCRONA",
        message=f"Usuário '{usuario['nome']}' ({usuario['role']}) consultou o sensor: {tipo}."
    )
    return {tipo: status_sincrono_sensores[tipo]}

def rodar_fastapi():
    uvicorn.run(app_fastapi, host="0.0.0.0", port=8000, log_level="warning")

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
        global dados_sensores, status_sincrono_sensores
        dados_validados = validar_json_payload(body)
        if dados_validados is None:
            log_mensagem(
                servico="dashboard-consumer",
                acao="VALIDAR_PAYLOAD",
                message="Mensagem corrompida ou inválida rejeitada na fila.",
                level="WARNING"
            )
            return
        tipo = dados_validados.get("tipo_sensor")
        dados_sensores[tipo] = dados_validados
        status_sincrono_sensores[tipo] = {
            "status": "Online",
            "ultima_verificacao": time.strftime('%H:%M:%S', time.localtime())
        }

    channel.basic_consume(queue='humidity_readings', on_message_callback=callback, auto_ack=True)
    channel.start_consuming()

app_flask = Flask(__name__)

HTML_PAGINA = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Painel de Monitoring Multissensor</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; background: #f4f6f9; margin: 0; padding: 20px; color: #333; }
        h1 { text-align: center; color: #2c3e50; margin-bottom: 5px; }
        .sub { text-align: center; color: #7f8c8d; margin-bottom: 30px; font-size: 14px; }
        .container { display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; }
        .card { background: white; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); padding: 20px; width: 280px; position: relative; transition: all 0.3s; }
        .dado { font-size: 26px; font-weight: bold; margin: 15px 0; color: #2c3e50; }
        .meta { font-size: 11px; color: #95a5a6; word-break: break-all; }
        .status-badge { position: absolute; top: 20px; right: 20px; font-size: 11px; padding: 3px 8px; border-radius: 12px; font-weight: bold; }
        .badge-online { background: #e8f8f5; color: #2ecc71; }
        .badge-offline { background: #fce4d6; color: #e74c3c; }
    </style>
    <script>
        setInterval(async () => {
            try {
                const resDados = await fetch('/api/sensors/current');
                const dados = await resDados.json();
                
                const resStatus = await fetch('http://' + window.location.hostname + ':8000/api/sensors/status', {
                    headers: { 'X-API-KEY': 'token-admin-123' }
                });
                const statusSincrono = await resStatus.json();
                
                const container = document.getElementById('cards-container');
                if (Object.keys(dados).length === 0) return;
                container.innerHTML = '';
                
                for (const [tipo, payload] of Object.entries(dados)) {
                    let valor = ''; let cor = '#3498db';
                    if (tipo === 'humidity') { valor = payload.humidity + '%'; cor = '#3498db'; }
                    else if (tipo === 'wind') { valor = payload.wind_speed + ' km/h'; cor = '#2ecc71'; }
                    else if (tipo === 'luminosity') { valor = payload.luminosity + ' lux'; cor = '#f1c40f'; }
                    else if (tipo === 'pressure') { valor = payload.pressure + ' hPa'; cor = '#9b59b6'; }
                    else if (tipo === 'temperature') { valor = payload.temperature + '°C'; cor = '#e74c3c'; }

                    const info = statusSincrono[tipo] || { "status": "Inativo", "ultima_verificacao": "-" };
                    const badgeClass = info.status === "Online" ? "badge-online" : "badge-offline";

                    container.innerHTML += `
                        <div class="card" style="border-top: 5px solid ${cor}">
                            <span class="status-badge ${badgeClass}">${info.status}</span>
                            <h2>${tipo.toUpperCase()}</h2>
                            <div class="dado">${valor}</div>
                            <div class="meta">
                                <p><strong>ID Correlação:</strong><br>${payload.correlation_id}</p>
                                <p>Atualizado: ${info.ultima_verificacao}</p>
                            </div>
                        </div>`;
                }
            } catch(e) {}
        }, 1500);
    </script>
</head>
<body>
    <h1>📊 Painel Central de Sensores Distribuídos</h1>
    <div class="sub">Segurança Ativada: Controle de Acesso por Papéis (RBAC) e Autenticação via Cabeçalho</div>
    <div class="container" id="cards-container">
        <p class="vazio">Aguardando sinais dos sensores na fila do RabbitMQ...</p>
    </div>
</body>
</html>
"""

@app_flask.route('/', methods=['GET'])
def home(): return render_template_string(HTML_PAGINA)

@app_flask.route('/api/sensors/current', methods=['GET'])
def get_all_sensors(): return jsonify(dados_sensores), 200

if __name__ == '__main__':
    threading.Thread(target=iniciar_consumidor_fila, daemon=True).start()
    threading.Thread(target=rodar_fastapi, daemon=True).start()
    app_flask.run(host='0.0.0.0', port=8080)