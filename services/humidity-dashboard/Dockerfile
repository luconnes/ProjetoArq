FROM python:3.10-slim
WORKDIR /app
RUN pip install pika flask


COPY ./middleware /app/middleware
COPY ./services/humidity-dashboard/dashboard.py .

CMD ["python", "-u", "dashboard.py"]
