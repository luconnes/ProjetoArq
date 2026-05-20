import uuid
import datetime
import json
CHAVES_OBRIGATORIAS_PAYLOAD = {"correlation_id", "sensor_id", "humidity", "timestamp"}
def validar_json_payload(body_string):
   
    try:
        dados = json.loads(body_string)
        
       
        if not isinstance(dados, dict):
            return None
            
       
        if not CHAVES_OBRIGATORIAS_PAYLOAD.issubset(dados.keys()):
            return None
            
        return dados
    except (json.JSONDecodeError, TypeError):
        return None



def log_mensagem(servico, acao, message, correlation_id=None, level="INFO"):
    orte a níveis de segurança (INFO, WARNING, SECURITY_ALERT).
    
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
        
    log_estruturado = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "level": level,
        "servico": servico,
        "acao": acao,
        "correlation_id": correlation_id,
        "mensagem": message
    }
    
    print(json.dumps(log_estruturado), flush=True)
    return correlation_id
