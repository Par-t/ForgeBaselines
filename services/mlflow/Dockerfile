FROM python:3.11-slim

WORKDIR /mlflow

# Install mlflow
RUN pip install --no-cache-dir mlflow==2.10.0

# Create directories for artifacts and database
RUN mkdir -p /mlflow-artifacts

# Expose port
EXPOSE 5000

# Run MLflow server with SQLite backend
CMD ["mlflow", "server", \
     "--host", "0.0.0.0", \
     "--port", "5000", \
     "--backend-store-uri", "sqlite:///mlflow.db", \
     "--default-artifact-root", "/mlflow-artifacts"]