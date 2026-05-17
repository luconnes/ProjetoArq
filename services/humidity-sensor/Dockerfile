FROM python:3.10-slim

WORKDIR /app

# Instala a biblioteca padrão para conectar ao RabbitMQ
RUN pip install pika

COPY sensor.py .

CMD ["python", "-u", "sensor.py"]