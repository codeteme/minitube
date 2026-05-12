import pytest
from src.admin_service.tests.conftest import seed_user


def test_user_count_returns_total_and_active(client, db):
    """Test GET /admin/users/count returns user statistics."""
    # Seed users: 3 active, 1 inactive
    seed_user(db, name="Alice", email="alice@test.com", role="user", is_active=True)
    seed_user(db, name="Bob", email="bob@test.com", role="user", is_active=True)
    seed_user(db, name="Carol", email="carol@test.com", role="admin", is_active=True)
    seed_user(db, name="Dave", email="dave@test.com", role="user", is_active=False)

    resp = client.get("/admin/users/count")
    assert resp.status_code == 200
    body = resp.json()

    assert "total" in body
    assert "active" in body
    assert body["total"] == 4
    assert body["active"] == 3


def test_user_count_empty_database(client, db):
    """Test GET /admin/users/count returns zero counts when no users exist."""
    resp = client.get("/admin/users/count")
    assert resp.status_code == 200
    body = resp.json()

    assert body["total"] == 0
    assert body["active"] == 0


def test_ban_user_sets_is_active_false(client, db):
    """Test PATCH /admin/users/{user_id}/ban successfully bans a user."""
    user = seed_user(db, name="Eve", email="eve@test.com", role="user", is_active=True)

    resp = client.patch(f"/admin/users/{user.id}/ban")
    assert resp.status_code == 200
    body = resp.json()

    assert body["user_id"] == user.id
    assert body["banned"] is True

    # Verify user is actually banned in database
    resp_count = client.get("/admin/users/count")
    count_body = resp_count.json()
    assert count_body["active"] == 0  # User should be inactive now


def test_ban_nonexistent_user_returns_404(client, db):
    """Test PATCH /admin/users/{user_id}/ban returns 404 for non-existent user."""
    resp = client.patch("/admin/users/99999/ban")
    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"] == "User not found"


def test_ban_already_banned_user(client, db):
    """Test banning an already-banned user returns success."""
    user = seed_user(db, name="Frank", email="frank@test.com", role="user", is_active=False)

    resp = client.patch(f"/admin/users/{user.id}/ban")
    assert resp.status_code == 200
    body = resp.json()
    assert body["banned"] is True


def test_reset_password_by_email_returns_success(client, db):
    """Test POST /admin/auth/reset triggers password reset for valid email."""
    seed_user(db, name="Grace", email="grace@test.com", role="admin", is_active=True)

    resp = client.post("/admin/auth/reset?email=grace@test.com")
    assert resp.status_code == 200
    body = resp.json()

    assert body["email"] == "grace@test.com"
    assert body["reset_sent"] is True


def test_reset_password_nonexistent_email_returns_404(client, db):
    """Test POST /admin/auth/reset returns 404 for non-existent email."""
    resp = client.post("/admin/auth/reset?email=nobody@test.com")
    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"] == "User not found"


def test_reset_password_email_case_sensitive(client, db):
    """Test that email lookup is case-sensitive (as stored in DB)."""
    seed_user(db, name="Henry", email="henry@test.com", role="user", is_active=True)

    # Try with different case
    resp = client.post("/admin/auth/reset?email=HENRY@TEST.COM")
    assert resp.status_code == 404
