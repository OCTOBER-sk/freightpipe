"""Tests for user authentication — register, login, JWT, dual auth."""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from freightpipe.api.auth import get_account_id
from freightpipe.api.auth_jwt import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from freightpipe.api.routes import router

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_USER_ID = uuid4()
TEST_ACCOUNT_ID = uuid4()
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "securepass123"
TEST_API_KEY = "fp_live_test_key_12345"
TEST_KEY_HASH = hashlib.sha256(TEST_API_KEY.encode()).hexdigest()


class FakeRecord(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


def _record(d: dict) -> FakeRecord:
    return FakeRecord(d)


class _CtxMgr:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


def _make_mock_pool(conn):
    pool = MagicMock()
    pool.acquire.return_value = _CtxMgr(conn)
    return pool


def _make_app():
    app = FastAPI()
    app.include_router(router)
    return app


def _override_auth(app):
    async def _fake_auth():
        return TEST_ACCOUNT_ID
    app.dependency_overrides[get_account_id] = _fake_auth


def _now():
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    return _make_app()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-Api-Key": TEST_API_KEY}


@pytest.fixture
def jwt_token():
    return create_access_token(TEST_USER_ID, TEST_ACCOUNT_ID)


@pytest.fixture
def jwt_headers(jwt_token):
    return {"Authorization": f"Bearer {jwt_token}"}


# ---------------------------------------------------------------------------
# 1. Password hashing
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_hash_and_verify(self):
        pw = "mypassword123"
        hashed = hash_password(pw)
        assert hashed != pw
        assert verify_password(pw, hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_different_passwords_different_hashes(self):
        h1 = hash_password("password1")
        h2 = hash_password("password2")
        assert h1 != h2


# ---------------------------------------------------------------------------
# 2. JWT token creation and verification
# ---------------------------------------------------------------------------

class TestJWTToken:
    def test_create_and_decode(self):
        token = create_access_token(TEST_USER_ID, TEST_ACCOUNT_ID)
        payload = decode_access_token(token)
        assert payload["sub"] == str(TEST_USER_ID)
        assert payload["account_id"] == str(TEST_ACCOUNT_ID)
        assert "exp" in payload

    def test_decode_invalid_token_raises(self):
        with pytest.raises(ValueError, match="Invalid or expired token"):
            decode_access_token("not.a.valid.token")

    def test_decode_expired_token_raises(self):
        from datetime import timedelta

        from jose import jwt

        from freightpipe.api.auth_jwt import JWT_ALGORITHM, JWT_SECRET

        payload = {
            "sub": str(TEST_USER_ID),
            "account_id": str(TEST_ACCOUNT_ID),
            "exp": datetime.now(UTC) - timedelta(hours=1),
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        with pytest.raises(ValueError, match="Invalid or expired token"):
            decode_access_token(token)

    def test_roundtrip_uuids(self):
        uid = uuid4()
        aid = uuid4()
        token = create_access_token(uid, aid)
        payload = decode_access_token(token)
        assert payload["sub"] == str(uid)
        assert payload["account_id"] == str(aid)


# ---------------------------------------------------------------------------
# 3. POST /v1/auth/register
# ---------------------------------------------------------------------------

class TestRegister:
    def test_register_success(self, app, client):
        user_id = uuid4()
        account_id = uuid4()
        now = _now()

        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            # get_by_email -> None (no existing user)
            # create user -> user record
            # create account -> account record
            # update accounts set user_id -> not checked
            # create api_key -> key record
            conn.fetchrow = AsyncMock(side_effect=[
                None,  # get_by_email
                _record({  # create user
                    "id": user_id, "email": TEST_EMAIL, "phone": None,
                    "company_name": "Test Co", "password_hash": "hashed",
                    "is_active": True, "created_at": now, "updated_at": now,
                }),
                _record({  # create account
                    "id": account_id, "name": "Test Co",
                    "created_at": now, "llm_byok_keys": {},
                }),
                _record({  # create api_key
                    "id": uuid4(), "account_id": account_id,
                    "key_hash": "hash", "label": "Primary Key",
                    "created_at": now, "revoked_at": None,
                }),
            ])
            conn.execute = AsyncMock(return_value="UPDATE 1")
            mock_get_pool.return_value = _make_mock_pool(conn)

            resp = client.post("/v1/auth/register", json={
                "email": TEST_EMAIL,
                "company_name": "Test Co",
                "password": TEST_PASSWORD,
            })

        assert resp.status_code == 201
        data = resp.json()
        assert "user_id" in data
        assert "account_id" in data
        assert "token" in data
        assert "api_key" in data
        assert data["api_key"].startswith("fp_live_")

    def test_register_invalid_email(self, client):
        resp = client.post("/v1/auth/register", json={
            "email": "not-an-email",
            "company_name": "Test Co",
            "password": TEST_PASSWORD,
        })
        assert resp.status_code == 400
        assert resp.json()["detail"]["error"]["code"] == "validation_error"

    def test_register_short_password(self, client):
        resp = client.post("/v1/auth/register", json={
            "email": TEST_EMAIL,
            "company_name": "Test Co",
            "password": "short",
        })
        assert resp.status_code == 400
        assert "at least 8 characters" in resp.json()["detail"]["error"]["message"]

    def test_register_missing_company_name(self, client):
        resp = client.post("/v1/auth/register", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        })
        assert resp.status_code == 400

    def test_register_duplicate_email(self, client):
        now = _now()
        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(return_value=_record({
                "id": uuid4(), "email": TEST_EMAIL, "phone": None,
                "company_name": "Existing Co", "password_hash": "hashed",
                "is_active": True, "created_at": now, "updated_at": now,
            }))
            mock_get_pool.return_value = _make_mock_pool(conn)

            resp = client.post("/v1/auth/register", json={
                "email": TEST_EMAIL,
                "company_name": "Test Co",
                "password": TEST_PASSWORD,
            })

        assert resp.status_code == 409
        assert resp.json()["detail"]["error"]["code"] == "email_taken"


# ---------------------------------------------------------------------------
# 4. POST /v1/auth/login
# ---------------------------------------------------------------------------

class TestLogin:
    def test_login_success(self, client):
        pw_hash = hash_password(TEST_PASSWORD)
        now = _now()

        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(side_effect=[
                _record({  # get_by_email
                    "id": TEST_USER_ID, "email": TEST_EMAIL, "phone": None,
                    "company_name": "Test Co", "password_hash": pw_hash,
                    "is_active": True, "created_at": now, "updated_at": now,
                }),
                _record({"id": TEST_ACCOUNT_ID}),  # account lookup
            ])
            mock_get_pool.return_value = _make_mock_pool(conn)

            resp = client.post("/v1/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == str(TEST_USER_ID)
        assert data["account_id"] == str(TEST_ACCOUNT_ID)
        assert "token" in data

        # Verify the returned JWT is valid
        payload = decode_access_token(data["token"])
        assert payload["sub"] == str(TEST_USER_ID)

    def test_login_wrong_password(self, client):
        pw_hash = hash_password(TEST_PASSWORD)
        now = _now()

        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(return_value=_record({
                "id": TEST_USER_ID, "email": TEST_EMAIL, "phone": None,
                "company_name": "Test Co", "password_hash": pw_hash,
                "is_active": True, "created_at": now, "updated_at": now,
            }))
            mock_get_pool.return_value = _make_mock_pool(conn)

            resp = client.post("/v1/auth/login", json={
                "email": TEST_EMAIL,
                "password": "wrongpassword",
            })

        assert resp.status_code == 401
        assert resp.json()["detail"]["error"]["code"] == "invalid_credentials"

    def test_login_nonexistent_user(self, client):
        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(return_value=None)
            mock_get_pool.return_value = _make_mock_pool(conn)

            resp = client.post("/v1/auth/login", json={
                "email": "nobody@example.com",
                "password": TEST_PASSWORD,
            })

        assert resp.status_code == 401

    def test_login_missing_fields(self, client):
        resp = client.post("/v1/auth/login", json={"email": TEST_EMAIL})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 5. GET /v1/auth/me
# ---------------------------------------------------------------------------

class TestGetMe:
    def test_me_with_jwt(self, app, client, jwt_headers):
        _override_auth(app)
        now = _now()

        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(return_value=_record({
                "id": TEST_USER_ID, "email": TEST_EMAIL, "phone": "555-1234",
                "company_name": "Test Co", "password_hash": "hashed",
                "is_active": True, "created_at": now, "updated_at": now,
            }))
            mock_get_pool.return_value = _make_mock_pool(conn)

            resp = client.get("/v1/auth/me", headers=jwt_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == str(TEST_USER_ID)
        assert data["email"] == TEST_EMAIL
        assert data["phone"] == "555-1234"
        assert data["company_name"] == "Test Co"

    def test_me_with_api_key_fails(self, app, client, auth_headers):
        """GET /auth/me requires JWT — API key alone should fail."""
        _override_auth(app)
        resp = client.get("/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 6. PUT /v1/auth/profile
# ---------------------------------------------------------------------------

class TestUpdateProfile:
    def test_update_profile(self, app, client, jwt_headers):
        _override_auth(app)
        now = _now()

        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(return_value=_record({
                "id": TEST_USER_ID, "email": TEST_EMAIL, "phone": "555-9999",
                "company_name": "Updated Co", "password_hash": "hashed",
                "is_active": True, "created_at": now, "updated_at": now,
            }))
            mock_get_pool.return_value = _make_mock_pool(conn)

            resp = client.put(
                "/v1/auth/profile",
                headers=jwt_headers,
                json={"phone": "555-9999", "company_name": "Updated Co"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["phone"] == "555-9999"
        assert data["company_name"] == "Updated Co"

    def test_update_profile_with_api_key_fails(self, app, client, auth_headers):
        """PUT /auth/profile requires JWT — API key alone should fail."""
        _override_auth(app)
        resp = client.put(
            "/v1/auth/profile",
            headers=auth_headers,
            json={"phone": "555-9999"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 7. Dual auth — both API key and JWT work on protected endpoints
# ---------------------------------------------------------------------------

class TestDualAuth:
    def test_api_key_auth_on_jobs(self, app, client, auth_headers):
        """Existing API key auth still works on /v1/jobs."""
        _override_auth(app)
        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetch = AsyncMock(return_value=[])
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.get("/v1/jobs", headers=auth_headers)
        assert resp.status_code == 200

    def test_jwt_auth_on_jobs(self, app, client, jwt_headers):
        """JWT auth works on /v1/jobs."""
        _override_auth(app)
        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetch = AsyncMock(return_value=[])
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.get("/v1/jobs", headers=jwt_headers)
        assert resp.status_code == 200

    def test_no_auth_returns_401(self, client):
        """No credentials at all returns 401."""
        resp = client.get("/v1/jobs")
        assert resp.status_code == 401

    def test_invalid_both_returns_401(self, client):
        """Both invalid credentials returns 401."""
        with patch("freightpipe.api.auth.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(return_value=None)
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.get("/v1/jobs", headers={
                "Authorization": "Bearer invalid.token.here",
                "X-Api-Key": "bad_key",
            })
        assert resp.status_code == 401

    def test_jwt_takes_precedence_over_api_key(self, app, client):
        """When both are provided and JWT is valid, JWT is used."""
        _override_auth(app)
        token = create_access_token(TEST_USER_ID, TEST_ACCOUNT_ID)
        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetch = AsyncMock(return_value=[])
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.get("/v1/jobs", headers={
                "Authorization": f"Bearer {token}",
                "X-Api-Key": "some_key",
            })
        assert resp.status_code == 200
