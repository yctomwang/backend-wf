import pytest
import flask.testing

from pytest_mock import MockerFixture

@pytest.fixture
def app():
    """Flask application from test project instance"""
    from app import app
    app.config.update(
        {
            "TESTING": True,
            "ENGINEERING_ORDERS_SERVICE_URL":  "http://127.0.0.1:5079"
        }
    )
    return app


@pytest.fixture
def mocked_db_app(mocker: MockerFixture):
    """Flask application from test project instance"""
    from app import app

    mocker.patch("app.models.db")

    app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "postgresql://test_pam:test_pam@127.0.0.1:5432/test_pam",
            "ENGINEERING_ORDERS_SERVICE_URL":  "http://127.0.0.1:5079"
        }
    )

    with app.app_context():
        yield app