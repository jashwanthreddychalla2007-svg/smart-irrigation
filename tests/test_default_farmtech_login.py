"""
Unit and Integration tests for default 'farmtech' user credentials (123456).
Verifies:
1. Default farmer account exists and authenticates with password '123456'.
2. Farmer login endpoint (/api/auth/login) returns success and redirects to /dashboard.
3. Super Admin login endpoint (/api/admin/auth/login) succeeds with 'farmtech' / '123456'.
4. Incorrect credentials are appropriately rejected.
"""

import pytest
from app import app
from src.farm_manager import (
    init_farm_db,
    seed_default_farmtech_account,
    authenticate_farmer,
    get_farmer_farms,
    get_farm_sections,
)
from src.admin_manager import (
    init_admin_db,
    bootstrap_super_admin,
    authenticate_admin,
)


@pytest.fixture(autouse=True)
def setup_databases():
    """Ensure farmtech account is provisioned."""
    init_farm_db()
    seed_default_farmtech_account()
    init_admin_db()
    bootstrap_super_admin()


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_farmtech_farmer_authentication():
    """Farmer authentication succeeds with username 'farmtech' and password '123456'."""
    farmer = authenticate_farmer("farmtech", "123456")
    assert farmer is not None
    assert farmer["username"] == "farmtech"
    assert farmer["status"] == "Active"
    assert farmer["onboarding_completed"] is True

    # Farm and sections
    farms = get_farmer_farms(farmer["id"])
    assert len(farms) >= 1
    sections = get_farm_sections(farms[0]["id"], farmer["id"])
    assert len(sections) >= 3


def test_farmtech_farmer_login_endpoint(client):
    """POST /api/auth/login succeeds for farmtech / 123456."""
    res = client.post("/api/auth/login", json={
        "username": "farmtech",
        "password": "123456"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["farmer"]["username"] == "farmtech"
    assert data["redirect"] == "/dashboard"


def test_farmtech_admin_login_endpoint(client):
    """POST /api/admin/auth/login succeeds for farmtech / 123456."""
    admin_auth = authenticate_admin("farmtech", "123456")
    assert admin_auth["authenticated"] is True

    res = client.post("/api/admin/auth/login", json={
        "username": "farmtech",
        "password": "123456"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["admin"]["username"] == "farmtech"


def test_farmtech_invalid_password_rejected(client):
    """Invalid password for farmtech is rejected."""
    farmer = authenticate_farmer("farmtech", "wrongpassword")
    assert farmer is None

    res = client.post("/api/auth/login", json={
        "username": "farmtech",
        "password": "wrongpassword"
    })
    assert res.status_code == 401
