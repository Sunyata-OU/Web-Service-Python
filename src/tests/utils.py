import os

from fastapi.testclient import TestClient

from src.main import create_app

# Set test environment variables before importing the app
test_env_vars = {
    "POSTGRES_USER": "test_user",
    "POSTGRES_PASSWORD": "test_pass",
    "POSTGRES_SERVER": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "test_db",
    "S3_ACCESS_KEY_ID": "test_key",
    "S3_ACCESS_KEY": "test_secret",
    "ENVIRONMENT": "testing",
    "DEBUG": "false",
}

for key, value in test_env_vars.items():
    os.environ[key] = value

# Create test application
app = create_app()
client = TestClient(app)
