FROM python:3.11-slim

WORKDIR /app

COPY services/dashboard/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/dashboard/ /app/
COPY middleware/ /app/middleware/

RUN mkdir -p /app/data

EXPOSE 8080
EXPOSE 8000

CMD ["python", "dashboard.py"]