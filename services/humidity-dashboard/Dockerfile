FROM python:3.10-slim

WORKDIR /app

# Instala o Flask para a API REST (Síncrona) e o Pika para a Fila (Assíncrona)
RUN pip install flask pika

COPY dashboard.py .

EXPOSE 8080

CMD ["python", "-u", "dashboard.py"]