FROM python:3.14.8-slim
WORKDIR /app
COPY replica.py experiment.py ./
ENV PYTHONUNBUFFERED=1
CMD ["python", "replica.py"]
