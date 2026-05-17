FROM python:3.10-slim

WORKDIR /app


RUN pip install pika

COPY sensor.py .

CMD ["python", "-u", "sensor.py"]