"""Router for Google OAuth 2.0 authentication and linking."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.config import settings
from app.services.google_service import build_oauth_flow, get_user_info
from app.services.auth_service import (
    find_or_create_google_user,
    link_google_account,
    create_access_token,
    decode_access_token,
    get_user_by_id,
)

router = APIRouter(prefix="/auth/google", tags=["google-auth"])


@router.get("/login")
def google_login(token: str | None = Query(None, description="Optional JWT of current user to link account")):
    """Redirect to Google's OAuth consent screen.

    If token is provided, it is passed in the state to link Google to the logged-in user.
    """
    # Use token as state, or 'signup' if not logged in
    state = token if token else "signup"
    try:
        flow = build_oauth_flow(state=state)
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return {"auth_url": authorization_url}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Google login URL: {str(e)}"
        )


@router.get("/callback")
def google_callback(code: str, state: str, db: Session = Depends(get_db)):
    """Handle the OAuth redirect callback.

    Exchanges authorization code for access/refresh tokens, gets user details,
    links or creates a User, and redirects to frontend with a JWT.
    """
    try:
        # 1. Exchange auth code for credentials
        flow = build_oauth_flow(state=state)
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # 2. Get user profile info
        user_info = get_user_info(credentials)
        email = user_info.get("email")
        name = user_info.get("name")
        google_id = user_info.get("google_id")

        if not email or not google_id:
            raise ValueError("Failed to retrieve email or Google ID from Google account.")

        # 3. Determine if linking to an existing session
        linked_user = None
        if state and state != "signup":
            # Attempt to decode JWT passed as state
            current_user_id = decode_access_token(state)
            if current_user_id:
                current_user = get_user_by_id(db, current_user_id)
                if current_user:
                    # Link Google to current user
                    linked_user = link_google_account(
                        db=db,
                        user=current_user,
                        google_id=google_id,
                        access_token=credentials.token,
                        refresh_token=credentials.refresh_token,
                    )

        # 4. If not linking, execute standard find-or-create logic
        if not linked_user:
            linked_user = find_or_create_google_user(
                db=db,
                google_id=google_id,
                email=email,
                name=name,
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
            )

        # 5. Issue access token
        jwt_token = create_access_token(linked_user.id)

        # Redirect back to frontend callback route with token
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/google/callback?token={jwt_token}"
        )

    except Exception as e:
        # Redirect back to frontend callback route with error message
        error_msg = str(e).replace("\n", " ")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/google/callback?error={error_msg}"
        )
