FROM python:3.10-slim

WORKDIR /app

COPY services/dashboard/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY middleware/ ./middleware/
COPY services/dashboard/ ./src/

EXPOSE 8080 8000


CMD ["python", "-m", "src.dashboard"]