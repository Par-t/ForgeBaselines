FROM python:3.11-slim

WORKDIR /mlflow

# Install mlflow + boto3 (required for S3 artifact storage)
RUN pip install --no-cache-dir mlflow==2.10.0 boto3==1.34.0

# Create directory for local artifact fallback
RUN mkdir -p /mlflow-artifacts

EXPOSE 5000

# MLFLOW_ARTIFACT_ROOT is set via docker-compose environment:
#   local mode: /mlflow-artifacts (default)
#   s3 mode:    s3://your-bucket/mlflow
CMD ["sh", "-c", "mlflow server \
     --host 0.0.0.0 \
     --port 5000 \
     --backend-store-uri sqlite:///mlflow.db \
     --artifacts-destination ${MLFLOW_ARTIFACT_ROOT:-/mlflow-artifacts} \
     --serve-artifacts"]