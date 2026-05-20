FROM python:3.10-slim
WORKDIR /app
RUN pip install pika
COPY ./middleware /app/middleware
COPY ./services/humidity-sensor/sensor.py .
CMD ["python", "-u", "sensor.py"]