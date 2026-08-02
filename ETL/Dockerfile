FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY etl/requirements.txt ./etl-requirements.txt
RUN pip install --no-cache-dir -r etl-requirements.txt

COPY ETL ./ETL

CMD ["python", "-m", "ETL.pipeline"]
