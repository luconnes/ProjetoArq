FROM python:3.10-slim

WORKDIR /app


RUN pip install flask pika

COPY dashboard.py .

EXPOSE 8080

CMD ["python", "-u", "dashboard.py"]