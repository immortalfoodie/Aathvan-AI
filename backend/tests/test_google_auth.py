"""Tests for Google OAuth 2.0 and linkage endpoints."""

from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.models.user import User


@patch("app.routers.google_auth.build_oauth_flow")
def test_google_login_redirect_url(mock_build_flow, client):
    """Test generating the Google consent URL redirect info."""
    mock_flow = MagicMock()
    mock_flow.authorization_url.return_value = ("https://mock-google-consent-screen.com", "state")
    mock_build_flow.return_value = mock_flow

    # Call login endpoint
    resp = client.get("/auth/google/login")
    assert resp.status_code == 200
    assert resp.json()["auth_url"] == "https://mock-google-consent-screen.com"
    mock_flow.authorization_url.assert_called_once()


@patch("app.routers.google_auth.get_user_info")
@patch("app.routers.google_auth.build_oauth_flow")
def test_google_callback_creates_new_user(mock_build_flow, mock_get_user_info, client, db):
    """Test that Google callback successfully registers a new user if not exist."""
    mock_flow = MagicMock()
    mock_flow.credentials.token = "mock_access_token"
    mock_flow.credentials.refresh_token = "mock_refresh_token"
    mock_build_flow.return_value = mock_flow

    mock_get_user_info.return_value = {
        "email": "new-oauth-user@example.com",
        "name": "Google Signup User",
        "google_id": "google_99999",
    }

    # Verify user does not exist yet
    assert db.query(User).filter(User.google_id == "google_99999").first() is None

    # Call callback endpoint (follow_redirects=False because it redirects to frontend)
    resp = client.get("/auth/google/callback?code=mock_code&state=signup", follow_redirects=False)
    assert resp.status_code == 307  # Redirect code
    assert "/auth/google/callback?token=" in resp.headers["location"]

    # Verify user is created in database
    user = db.query(User).filter(User.google_id == "google_99999").first()
    assert user is not None
    assert user.email == "new-oauth-user@example.com"
    assert user.name == "Google Signup User"
    assert user.hashed_password is None  # standard password not set
    assert user.google_access_token == "mock_access_token"
    assert user.google_refresh_token == "mock_refresh_token"


@patch("app.routers.google_auth.get_user_info")
@patch("app.routers.google_auth.build_oauth_flow")
def test_google_callback_links_existing_user(mock_build_flow, mock_get_user_info, client, db, auth_headers):
    """Test that Google callback links to an existing user session if JWT is passed as state."""
    # Find user ID from database using standard credentials setup
    # In tests, user_id=1 exists
    existing_user = db.query(User).filter(User.id == 1).first()
    assert existing_user is not None
    assert existing_user.google_id is None

    mock_flow = MagicMock()
    mock_flow.credentials.token = "mock_access_token_2"
    mock_flow.credentials.refresh_token = "mock_refresh_token_2"
    mock_build_flow.return_value = mock_flow

    mock_get_user_info.return_value = {
        "email": existing_user.email,
        "name": "Linked User Name",
        "google_id": "google_88888",
    }

    # Extract JWT from headers ('Bearer <token>')
    token = auth_headers["Authorization"].split(" ")[1]

    # Call callback endpoint passing standard JWT as state
    resp = client.get(f"/auth/google/callback?code=mock_code&state={token}", follow_redirects=False)
    assert resp.status_code == 307

    # Verify Google ID has been linked to existing user
    db.refresh(existing_user)
    assert existing_user.google_id == "google_88888"
    assert existing_user.google_access_token == "mock_access_token_2"
    assert existing_user.google_refresh_token == "mock_refresh_token_2"
