"""Pruebas unitarias del verificador de JWT de Supabase."""

import json
import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm

from app.core.auth import InvalidTokenError, SupabaseTokenVerifier

SUPABASE_URL = "https://test-project.supabase.co"
ISSUER = f"{SUPABASE_URL}/auth/v1"
KID = "test-key-1"


@pytest.fixture(scope="module")
def ec_key():
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture
def verifier(ec_key, monkeypatch) -> SupabaseTokenVerifier:
    public_jwk = json.loads(ECAlgorithm.to_jwk(ec_key.public_key()))
    public_jwk.update({"kid": KID, "use": "sig", "alg": "ES256"})
    jwks = {"keys": [public_jwk]}

    monkeypatch.setattr(
        "jwt.jwks_client.PyJWKClient.fetch_data", lambda self: jwks
    )
    return SupabaseTokenVerifier(SUPABASE_URL, jwt_secret="legacy-secret")


def make_token(ec_key, **overrides) -> str:
    now = int(time.time())
    claims = {
        "sub": str(uuid.uuid4()),
        "email": "pepe@example.com",
        "role": "authenticated",
        "aud": "authenticated",
        "iss": ISSUER,
        "iat": now,
        "exp": now + 3600,
        "user_metadata": {"username": "pepe"},
    }
    claims.update(overrides)
    return jwt.encode(claims, ec_key, algorithm="ES256", headers={"kid": KID})


def test_valid_es256_token(verifier, ec_key):
    user_id = uuid.uuid4()
    user = verifier.verify(make_token(ec_key, sub=str(user_id)))
    assert user.id == user_id
    assert user.email == "pepe@example.com"
    assert user.role == "authenticated"
    assert user.claims["user_metadata"]["username"] == "pepe"


def test_expired_token_rejected(verifier, ec_key):
    with pytest.raises(InvalidTokenError):
        verifier.verify(make_token(ec_key, exp=int(time.time()) - 10))


def test_wrong_audience_rejected(verifier, ec_key):
    with pytest.raises(InvalidTokenError):
        verifier.verify(make_token(ec_key, aud="anon"))


def test_wrong_issuer_rejected(verifier, ec_key):
    with pytest.raises(InvalidTokenError):
        verifier.verify(make_token(ec_key, iss="https://evil.example.com/auth/v1"))


def test_token_signed_by_other_key_rejected(verifier):
    other_key = ec.generate_private_key(ec.SECP256R1())
    with pytest.raises(InvalidTokenError):
        verifier.verify(make_token(other_key))


def test_non_uuid_subject_rejected(verifier, ec_key):
    with pytest.raises(InvalidTokenError):
        verifier.verify(make_token(ec_key, sub="not-a-uuid"))


def test_hs256_legacy_secret_accepted(verifier):
    now = int(time.time())
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "aud": "authenticated", "iss": ISSUER,
         "iat": now, "exp": now + 60},
        "legacy-secret",
        algorithm="HS256",
    )
    assert verifier.verify(token).role == "authenticated"


def test_hs256_without_configured_secret_rejected(ec_key, monkeypatch):
    monkeypatch.setattr("jwt.jwks_client.PyJWKClient.fetch_data", lambda self: {"keys": []})
    verifier = SupabaseTokenVerifier(SUPABASE_URL, jwt_secret=None)
    now = int(time.time())
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "aud": "authenticated", "iss": ISSUER,
         "iat": now, "exp": now + 60},
        "anything",
        algorithm="HS256",
    )
    with pytest.raises(InvalidTokenError):
        verifier.verify(token)


def test_unsupported_algorithm_rejected(verifier):
    token = jwt.encode({"sub": str(uuid.uuid4())}, "", algorithm="none")
    with pytest.raises(InvalidTokenError):
        verifier.verify(token)
