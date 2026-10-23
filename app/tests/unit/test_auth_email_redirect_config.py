import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_development_can_omit_email_redirect():
    settings = Settings(_env_file=None, environment="development")
    assert settings.auth_email_redirect_to is None


def test_production_requires_email_redirect():
    with pytest.raises(ValidationError, match="AUTH_EMAIL_REDIRECT_TO es obligatorio"):
        Settings(_env_file=None, environment="production")


@pytest.mark.parametrize(
    "url",
    [
        "http://petpulse.example/verify",
        "https://localhost:3000/verify",
        "https://preview.localhost/verify",
        "https://127.0.0.1/verify",
    ],
)
def test_production_rejects_insecure_or_local_redirect(url):
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            auth_email_redirect_to=url,
        )


def test_production_accepts_https_redirect():
    settings = Settings(
        _env_file=None,
        environment="production",
        auth_email_redirect_to="https://petpulse.example/verify",
    )
    assert settings.auth_email_redirect_to == "https://petpulse.example/verify"


def test_redirect_must_be_absolute_http_url():
    with pytest.raises(ValidationError, match="URL absoluta"):
        Settings(_env_file=None, auth_email_redirect_to="/verify")
