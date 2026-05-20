FROM python:3.10-slim
WORKDIR /app
RUN pip install pika flask

# Copia a pasta middleware a partir da raiz do projeto
COPY ./middleware /app/middleware
COPY ./services/humidity-dashboard/dashboard.py .

CMD ["python", "-u", "dashboard.py"]