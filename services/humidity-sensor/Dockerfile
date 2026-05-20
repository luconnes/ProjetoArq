#aaaaaaaaaaaaaaaaaa

FROM python:3.10-slim
WORKDIR /app
RUN pip install pika

# Copia a pasta middleware a partir da raiz do projeto
COPY ./middleware /app/middleware
COPY ./services/humidity-sensor/sensor.py .

CMD ["python", "-u", "sensor.py"]