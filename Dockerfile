FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN apt-get update && apt-get install -y curl
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn","--bind","0.0.0.0:5000","app:app"]