"""Pruebas del adaptador sobre el SDK de Supabase, sin red."""

import uuid

import pytest
from supabase_auth.errors import AuthApiError, AuthSessionMissingError
from supabase_auth.types import Session, User

from app.application.interfaces.auth_service import AuthServiceError
from app.infrastructure.services.supabase_auth_service import (
    SupabaseAuthService,
    _to_session,
    _translate,
)


def test_requires_url_and_key():
    with pytest.raises(ValueError):
        SupabaseAuthService("", "key")
    with pytest.raises(ValueError):
        SupabaseAuthService("https://x.supabase.co", "")


def test_to_session_maps_sdk_session():
    user_id = uuid.uuid4()
    sdk_session = Session(
        access_token="acc", refresh_token="ref", expires_in=3600, token_type="bearer",
        user=User(id=str(user_id), app_metadata={}, user_metadata={}, aud="authenticated",
                  created_at="2026-10-14T00:00:00Z", email="ana@example.com"),
    )
    session = _to_session(sdk_session)
    assert session.user_id == user_id
    assert session.email == "ana@example.com"
    assert session.refresh_token == "ref"


def test_translate_invalid_credentials_is_401():
    exc = AuthApiError("Invalid login credentials", 400, "invalid_credentials")
    translated = _translate(exc)
    assert isinstance(translated, AuthServiceError)
    assert translated.status_code == 401
    assert translated.message == "Invalid login credentials"


def test_translate_keeps_provider_status():
    exc = AuthApiError("User already registered", 422, "user_already_exists")
    assert _translate(exc).status_code == 422


def test_translate_non_api_error_defaults_to_400():
    assert _translate(AuthSessionMissingError()).status_code == 400
