import os
from pathlib import Path


class BaseConfig:
    """Base configuration"""

    BASE_DIR = Path(__file__).parent.parent
    TESTING = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql://test_pam:test_pam@127.0.0.1:5432/test_pam"
    )
    CELERY_BROKER_URL = os.environ.get(
        "CELERY_BROKER_URL", "pyamqp://guest:guest@localhost//"
    )  # new
    CELERY_RESULT_BACKEND = os.environ.get(
        "CELERY_RESULT_BACKEND", "postgresql://test_pam:test_pam@127.0.0.1:5432/test_pam"
    )  # new


class DevelopmentConfig(BaseConfig):
    """Development configuration"""

    DEBUG = True


class ProductionConfig(BaseConfig):
    """Production configuration"""

    DEBUG = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
