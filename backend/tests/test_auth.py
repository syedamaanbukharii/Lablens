"""Test authentication."""
from lablens.auth.service import AuthService


def test_password_hashing():
    hashed = AuthService.hash_password("secure123")
    assert AuthService.verify_password("secure123", hashed)
    assert not AuthService.verify_password("wrong", hashed)


def test_jwt_round_trip():
    token = AuthService.create_token("user123", "test@test.com")
    payload = AuthService.decode_token(token)
    assert payload["sub"] == "user123"
    assert payload["email"] == "test@test.com"
