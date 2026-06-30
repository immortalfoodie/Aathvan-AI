"""Service for interacting with Google APIs (OAuth, Classroom, Calendar)."""

from datetime import datetime, timezone
import google.oauth2.credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

from app.config import settings
from app.models.user import User


def build_oauth_flow(state=None) -> Flow:
    """Build the Google OAuth 2.0 flow object with required scopes."""
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://accounts.google.com/o/oauth2/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }
    scopes = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/classroom.courses.readonly",
        "https://www.googleapis.com/auth/classroom.coursework.me.readonly",
        "https://www.googleapis.com/auth/calendar",
    ]
    flow = Flow.from_client_config(
        client_config,
        scopes=scopes,
        state=state,
    )
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    return flow


def get_google_credentials(user: User, db) -> google.oauth2.credentials.Credentials:
    """Rebuild Google credentials from database, refreshing tokens if expired."""
    creds = google.oauth2.credentials.Credentials(
        token=user.google_access_token,
        refresh_token=user.google_refresh_token,
        token_uri="https://accounts.google.com/o/oauth2/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )
    # Refresh the token if expired or about to expire
    if creds.expired or (creds.valid is False):
        try:
            creds.refresh(Request())
            # Save the refreshed access token and potentially new refresh token
            user.google_access_token = creds.token
            if creds.refresh_token:
                user.google_refresh_token = creds.refresh_token
            db.commit()
            db.refresh(user)
        except Exception as e:
            # If refresh fails, log or raise to prompt re-auth
            pass
    return creds


def get_classroom_service(user: User, db):
    """Get authenticated Google Classroom API client."""
    creds = get_google_credentials(user, db)
    return build("classroom", "v1", credentials=creds, static_discovery=False)


def get_calendar_service(user: User, db):
    """Get authenticated Google Calendar API client."""
    creds = get_google_credentials(user, db)
    return build("calendar", "v3", credentials=creds, static_discovery=False)


def get_user_info(credentials: google.oauth2.credentials.Credentials) -> dict:
    """Fetch user profile information using People API."""
    people_service = build("people", "v1", credentials=credentials, static_discovery=False)
    profile = people_service.people().get(
        resourceName="people/me",
        personFields="names,emailAddresses,metadata"
    ).execute()

    email = None
    if "emailAddresses" in profile and len(profile["emailAddresses"]) > 0:
        email = profile["emailAddresses"][0]["value"]

    name = "Google User"
    if "names" in profile and len(profile["names"]) > 0:
        name = profile["names"][0]["displayName"]

    # google_id is retrieved from resourceName metadata or directly via metadata
    google_id = None
    if "metadata" in profile and "sources" in profile["metadata"]:
        for source in profile["metadata"]["sources"]:
            if source.get("type") == "PROFILE":
                google_id = source.get("id")
                break

    # Fallback to general resourceName parse if profile id is missing
    if not google_id:
        google_id = profile.get("resourceName", "").replace("people/", "")

    return {
        "email": email,
        "name": name,
        "google_id": google_id,
    }
