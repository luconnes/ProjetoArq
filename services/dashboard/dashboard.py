import os
import sys
import time
import threading
import sqlite3
import pika

# Garanter que o contêiner localize a pasta compartilhada de middlewares
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append("/app")

from flask import Flask, jsonify, render_template_string
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware

# Importação dos middlewares centrais do projeto
from middleware.logger import log_mensagem, validar_json_payload

# =========================================================
# CONFIGURAÇÕES GERAIS
# =========================================================

broker_host = os.getenv("BROKER_HOST", "localhost")
# Alterado para a raiz de /app para evitar falhas de permissão de subpastas no Windows
DB_PATH = os.getenv("DB_PATH", "/app/telemetria.db")

TIMEOUT_SENSOR_ONLINE = 7

# =========================================================
# ESTADO EM MEMÓRIA
# =========================================================

dados_sensores = {}

status_sincrono_sensores = {
    "humidity": {"status": "Inativo", "ultima_verificacao": "-"},
    "wind": {"status": "Inativo", "ultima_verificacao": "-"},
    "luminosity": {"status": "Inativo", "ultima_verificacao": "-"},
    "pressure": {"status": "Inativo", "ultima_verificacao": "-"},
    "temperature": {"status": "Inativo", "ultima_verificacao": "-"}
}

# =========================================================
# SEGURANÇA RBAC
# =========================================================

USUARIOS_PERMISSOES = {
    "token-admin-123": {"nome": "Lucas", "role": "admin"},
    "token-usuario-456": {"nome": "Integrante", "role": "user"}
}

api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

# =========================================================
# SQLITE (PERSISTÊNCIA)
# =========================================================

def conectar_banco():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def inicializar_banco():
    # Cria a pasta base se necessário (no caso de caminhos customizados)
    diretorio_base = os.path.dirname(DB_PATH)
    if diretorio_base:
        os.makedirs(diretorio_base, exist_ok=True)

    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leituras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            correlation_id TEXT,
            sensor_id TEXT,
            tipo_sensor TEXT,
            valor REAL,
            timestamp REAL
        )
    """)

    conn.commit()
    conn.close()

    print(f"💾 [SQLITE] Banco inicializado com sucesso em: {DB_PATH}", flush=True)

def salvar_leitura_no_banco(dados):
    try:
        conn = conectar_banco()
        cursor = conn.cursor()

        tipo = dados.get("tipo_sensor")

        mapa_valores = {
            "humidity": "humidity",
            "wind": "wind_speed",
            "luminosity": "luminosity",
            "pressure": "pressure",
            "temperature": "temperature"
        }

        campo_valor = mapa_valores.get(tipo)
        valor = dados.get(campo_valor, 0)

        cursor.execute("""
            INSERT INTO leituras (
                correlation_id, sensor_id, tipo_sensor, valor, timestamp
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            dados.get("correlation_id"),
            dados.get("sensor_id"),
            tipo,
            valor,
            dados.get("timestamp")
        ))

        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM leituras")
        total = cursor.fetchone()[0]
        conn.close()

        print(f"💾 [SQLITE] Registro #{total} salvo com sucesso para o sensor ({tipo}) | Valor: {valor}", flush=True)

    except Exception as e:
        print(f"❌ [SQLITE ERRO] Falha crítica de inserção: {e}", flush=True)

# =========================================================
# AUTENTICAÇÃO E AUTORIZAÇÃO (RBAC)
# =========================================================

def obter_usuario_atual(token: str = Depends(api_key_header)):
    if not token or token not in USUARIOS_PERMISSOES:
        log_mensagem(
            servico="dashboard-security",
            acao="AUTENTICACAO",
            message="Tentativa de acesso com token inválido.",
            level="SECURITY_ALERT"
        )
        raise HTTPException(status_code=401, detail="Token inválido ou não fornecido.")
    return USUARIOS_PERMISSOES[token]

def verificar_admin(usuario=Depends(obter_usuario_atual)):
    if usuario["role"] != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado: privilégios de administrador requeridos.")
    return usuario 

# =========================================================
# API REST SÍNCRONA (FASTAPI)
# =========================================================

app_fastapi = FastAPI(title="API Middleware - Controle Síncrono")

app_fastapi.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app_fastapi.get("/api/sensors/status")
def status_sensores(usuario=Depends(verificar_admin)):
    agora = time.time()
    for tipo, payload in dados_sensores.items():
        ultimo_timestamp = payload.get("timestamp", 0)
        if agora - ultimo_timestamp > TIMEOUT_SENSOR_ONLINE:
            status_sincrono_sensores[tipo]["status"] = "Offline"
    return status_sincrono_sensores

@app_fastapi.get("/api/metrics")
def metricas(usuario=Depends(obter_usuario_atual)):
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT tipo_sensor, COUNT(*), AVG(valor)
            FROM leituras
            GROUP BY tipo_sensor
        """)
        rows = cursor.fetchall()
        conn.close()

        metricas_finais = {}
        for row in rows:
            metricas_finais[row[0]] = {
                "total_mensagens": row[1],
                "media": round(row[2], 2)
            }

        return {
            "status": "ok",
            "solicitante": usuario["nome"],
            "metricas": metricas_finais
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def rodar_fastapi():
    import uvicorn
    uvicorn.run(app_fastapi, host="0.0.0.0", port=8000, log_level="warning")

# =========================================================
# CONSUMIDOR ASÍNCRONO DE FILAS (AMQP / RABBITMQ)
# =========================================================

def iniciar_consumidor_fila():
    connection = None
    while not connection:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=broker_host)
            )
        except pika.exceptions.AMQPConnectionError:
            print("⏳ [AMQP] Aguardando inicialização do RabbitMQ...", flush=True)
            time.sleep(3)

    channel = connection.channel()

    filas = [
        "humidity_readings",
        "wind_readings",
        "luminosity_readings",
        "pressure_readings",
        "temperature_readings"
    ]

    def callback(ch, method, properties, body):
        global dados_sensores
        global status_sincrono_sensores

        dados = validar_json_payload(body)
        if dados is None:
            print("⚠️ [AMQP] Payload corrompido ou inválido rejeitado pelo middleware.", flush=True)
            return

        tipo = dados.get("tipo_sensor")
        dados_sensores[tipo] = dados
        status_sincrono_sensores[tipo] = {
            "status": "Online",
            "ultima_verificacao": time.strftime("%H:%M:%S")
        }

        salvar_leitura_no_banco(dados)

    for fila in filas:
        channel.queue_declare(queue=fila)
        channel.basic_consume(queue=fila, on_message_callback=callback, auto_ack=True)

    print("🚀 [AMQP] Consumidor assíncrono conectado com sucesso ao RabbitMQ.", flush=True)
    channel.start_consuming()

# =========================================================
# SERVIDOR INTERFACE GRAPHICA (FLASK)
# =========================================================

app_flask = Flask(__name__)

HTML_PAGINA = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<title>Dashboard Sensores</title>
<style>
body{ font-family: Arial; background:#f4f4f4; padding:20px; }
.container{ display:flex; flex-wrap:wrap; gap:20px; }
.card{ background:white; padding:20px; border-radius:10px; width:250px; box-shadow:0 0 10px rgba(0,0,0,0.1); }
.online{ color:green; font-weight: bold; }
.offline{ color:red; font-weight: bold; }
</style>
<script>
setInterval(async ()=>{
    try{
        const dadosResponse = await fetch('/api/sensors/current');
        const dados = await dadosResponse.json();

        const statusResponse = await fetch('http://' + window.location.hostname + ':8000/api/sensors/status', {
            headers:{ 'X-API-KEY':'token-admin-123' }
        });
        const status = await statusResponse.json();

        const container = document.getElementById('container');
        container.innerHTML = '';

        for(const [tipo,payload] of Object.entries(dados)){
            let valor = '';
            if(tipo === 'humidity') valor = payload.humidity + '%';
            else if(tipo === 'wind') valor = payload.wind_speed + ' km/h';
            else if(tipo === 'luminosity') valor = payload.luminosity + ' lux';
            else if(tipo === 'pressure') valor = payload.pressure + ' hPa';
            else if(tipo === 'temperature') valor = payload.temperature + ' °C';

            const sensorStatus = status[tipo] || { "status": "Offline", "ultima_verificacao": "-" };
            const classe = sensorStatus.status === 'Online' ? 'online' : 'offline';

            container.innerHTML += `
                <div class="card">
                    <h2>${tipo.toUpperCase()}</h2>
                    <h3>${valor}</h3>
                    <p class="${classe}">${sensorStatus.status}</p>
                    <small>Atualizado: ${sensorStatus.ultima_verificacao}</small>
                </div>`;
        }
    }catch(e){ console.log(e); }
}, 1500);
</script>
</head>
<body>
<h1>📊 Middleware Distribuído - Central de Monitorização</h1>
<div class="container" id="container"></div>
</body>
</html>
"""

@app_flask.route("/")
def home():
    return render_template_string(HTML_PAGINA)

@app_flask.route("/api/sensors/current")
def sensores_atuais():
    return jsonify(dados_sensores)

# =========================================================
# EXECUÇÃO ORQUESTRADA DO MIDDLEWARE
# =========================================================

if __name__ == "__main__":
    # 1. Garante a criação estruturada do arquivo do SQLite
    inicializar_banco()

    # 2. Inicializa o barramento assíncrono (RabbitMQ)
    threading.Thread(target=iniciar_consumidor_fila, daemon=True).start()

    # 3. Inicializa o barramento síncrono securizado (FastAPI)
    threading.Thread(target=rodar_fastapi, daemon=True).start()

    # 4. Inicia a interface principal do cliente
    app_flask.run(host="0.0.0.0", port=8080)