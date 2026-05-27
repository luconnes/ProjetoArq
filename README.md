# Sistema Distribuído de Telemetria Ambiental

Este projeto consiste em um ecossistema de microsserviços maduro, voltado para a coleta, processamento, validação e visualização de dados de telemetria ambiental em tempo real. A arquitetura foi projetada com base nos pilares de sistemas distribuídos, combinando abordagens síncronas e assíncronas, garantir a integridade dos dados na persistência e isolar o domínio de cada componente.

## Arquitetura e Papéis dos Componentes

O sistema é totalmente modularizado, composto por sete contêineres independentes de alto desempenho que interagem através de uma rede isolada:

1. **Broker de Mensageria (RabbitMQ):** Componente central que provê o desacoplamento temporal e espacial do sistema. Utilizando a imagem oficial com plugin de gerenciamento, ele opera como um buffer de dados seguro, organizando as mensagens em filas para mitigar picos de tráfego (backpressure).
2. **Central Dashboard (Flask & FastAPI):** Camada centralizada de ingestão e interface. Atua como o consumidor exclusivo das filas do RabbitMQ, processando mensagens assíncronas para persistência. Paralelamente, serve uma API REST síncrona de alta performance para a recuperação de dados históricos e uma interface web para visualização gráfica.
3. **Humidity Sensor :** Microsserviço que simula a captura contínua e o envio do percentual de umidade relativa do ar.
4. **Wind Sensor :** Microsserviço responsável pela geração de dados anemométricos complexos, computando a velocidade e a direção do vento.
5. **Luminosity Sensor :** Unidade focada na leitura e transmissão da intensidade de radiação lumínica em lux.
6. **Pressure Sensor :** Sensor voltado para o monitoramento barométrico da pressão atmosférica em hPa.
7. **Sensor Temperatura :** Dispositivo de amostragem térmica de alta frequência que monitora flutuações em graus Celsius.

---

## Engenharia de Software e Padrões Adotados

### 1. Infraestrutura como Código e Orquestração
A complexidade de subir e conectar múltiplos microsserviços manualmente foi resolvida através do gerenciamento centralizado com Docker Compose. O arquivo de configuração mapeia dependências determinísticas por meio de ordens de inicialização específicas. O uso de `healthchecks` no RabbitMQ garante que os componentes dependentes, como o Dashboard, segurem sua inicialização até que o broker esteja em estado saudável (`service_healthy`), prevenindo exceções de conexão na subida do ambiente.

### 2. Rede Isolada e Descoberta de Serviços
A comunicação interna ocorre dentro de uma rede virtual isolada com driver `bridge` (`middleware_network`). Esta abordagem mitiga riscos de segurança, pois os contêineres não expõem portas desnecessárias ao sistema hospedeiro. A descoberta de serviços é resolvida via DNS interno do Docker, onde os sensores localizam o broker utilizando apenas a string `rabbitmq`, abstraindo endereços IP estáticos.

### 3. Governança de Dados e Schema Enforcement
Para evitar o problema clássico de corrupção do banco de dados por envio de payloads malformados ou incompletos, o arquivo `middleware.py` foi posicionado como um Gatekeeper lógico do sistema. Ele intercepta o JSON recebido e executa uma validação estrita. Mensagens que não contenham chaves obrigatórias como `sensor_id`, `timestamp`, `tipo_sensor` e o respectivo valor numérico são descartadas imediatamente, gerando um log de erro controlado em vez de quebrar a linha de execução do consumidor.

### 4. Tolerância a Falhas e Alta Disponibilidade
O ecossistema foi projetado sob a premissa de que falhas em sistemas distribuídos são inevitáveis. As seguintes táticas de resiliência foram aplicadas:
* **Estratégia de Retry com Espera Ativa:** Os sensores possuem algoritmos de reconexão automática com intervalos de segurança. Caso a conexão com o broker seja interrompida, o sensor não finaliza seu processo; ele entra em um laço de tentativas até restabelecer a comunicação.
* **Isolamento Espacial e Temporal:** Se o Dashboard ou o banco de dados sofrerem uma queda crítica, os sensores continuam coletando dados e publicando no RabbitMQ. O broker retém a telemetria com segurança. Quando o Dashboard é reerguido, ele consome as mensagens acumuladas sem perda de informação.
* **Políticas de Auto-Recuperação:** Todos os serviços estão sob a diretiva `restart: always` do Docker, o que instrui o daemon do contêiner a reiniciar automaticamente qualquer processo que encerre devido a falhas internas ou estouro de memória.

### 5. Observabilidade e Tracing Distribuído
A depuração de sistemas assíncronos é complexa devido à falta de linearidade nas execuções. Para contornar esse problema, o sistema implementa:
* **Correlation ID:** Cada leitura gerada por um sensor recebe um identificador único universal (UUID). Esse identificador é injetado no payload e permanece atrelado ao dado durante o tráfego pelas filas e no momento da gravação no banco, permitindo rastrear o ciclo de vida completo de uma mensagem específica.
* **Logs Estruturados:** As saídas de console foram padronizadas em estruturas JSON.

### 6. Segurança Baseada em RBAC e Tokens
A segurança da camada síncrona bloqueia acessos indevidos por meio de dois mecanismos em FastAPI:
* **Autenticação por API Keys:** Os endpoints exigem a passagem de uma chave secreta no cabeçalho HTTP da requisição (`Authorization: Bearer <TOKEN>`), impedindo requisições de agentes externos anônimos.
* **Controle de Acesso Baseado em Papéis (RBAC):** O sistema diferencia as permissões dos tokens autenticados. Usuários com a regra `Viewer` possuem direitos estritos de leitura de dados no dashboard, enquanto contas com perfil `Admin` detêm privilégios para executar varreduras no histórico do banco e realizar tarefas administrativas.

---

## Fluxo da Informação 

1. O sensor simula ou coleta a métrica ambiental.
2. O sensor encapsula a leitura em um JSON, injeta o Correlation ID (UUID) e publica no broker RabbitMQ de forma assíncrona.
3. O RabbitMQ recebe a mensagem e a armazena em uma fila persistente dedicada à telemetria.
4. O consumidor interno do Central Dashboard remove a mensagem da fila.
5. O `middleware.py` executa o Schema Enforcement para validar o contrato do JSON.
6. Se válido, o dado é persistido no banco de dados relacional leve SQLite através de volumes mapeados.
7. O Dashboard em Flask lê o banco de dados e atualiza os gráficos da interface.
8. Usuários externos autenticados com API Keys consomem os dados históricos consultando a API FastAPI.

---

## Payload JSON

Qualque componente que publique na fila deve seguir o formato abaixo:

```json
{
  "correlation_id": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
  "sensor_id": "sensor_temperatura_01",
  "tipo_sensor": "temperatura",
  "valor": 24.5,
  "unidade": "C",
  "timestamp": "2026-05-27T19:57:25Z"
}
