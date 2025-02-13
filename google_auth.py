import json
import os
import logging
import requests
import secrets
from extensions import db
from flask import Blueprint, redirect, request, url_for, session, flash
from flask_login import login_required, login_user, logout_user
from models import User
from oauthlib.oauth2 import WebApplicationClient

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

GOOGLE_CLIENT_ID = os.environ["GOOGLE_OAUTH_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_OAUTH_CLIENT_SECRET"]
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Get the domain from environment or request
def get_redirect_url():
    """Get the correct redirect URL for the environment"""
    if request:
        # Get the domain from the request, using the most reliable header
        domain = (request.headers.get('X-Forwarded-Host') or 
                 request.headers.get('Host') or 
                 request.headers.get('X-Replit-User-Domain') or 
                 request.host)

        # Always use HTTPS for OAuth callbacks in production
        redirect_url = f"https://{domain}/google_login/callback"
        logger.info(f"Generated redirect URL: {redirect_url}")
        return redirect_url

    # Fallback for initialization (should rarely be used)
    return f"https://{os.environ.get('REPLIT_DEV_DOMAIN')}/google_login/callback"

# Print setup instructions
current_redirect_url = get_redirect_url()
print(f"""To make Google authentication work:
1. Go to https://console.cloud.google.com/apis/credentials
2. Create a new OAuth 2.0 Client ID
3. Add {current_redirect_url} to Authorized redirect URIs

For detailed instructions, see:
https://docs.replit.com/additional-resources/google-auth-in-flask#set-up-your-oauth-app--client
""")

# Allow OAuth over HTTP for development only
if os.environ.get('FLASK_DEBUG'):
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

client = WebApplicationClient(GOOGLE_CLIENT_ID)

google_auth = Blueprint("google_auth", __name__)

@google_auth.route("/google_login")
def login():
    try:
        logger.debug("Starting Google login process")

        # Generate and store a random state parameter
        session['oauth_state'] = secrets.token_urlsafe(32)
        redirect_uri = get_redirect_url()
        logger.debug(f"Using redirect URL: {redirect_uri}")

        google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
        authorization_endpoint = google_provider_cfg["authorization_endpoint"]

        request_uri = client.prepare_request_uri(
            authorization_endpoint,
            redirect_uri=redirect_uri,
            scope=["openid", "email", "profile"],
            state=session['oauth_state']
        )
        logger.debug(f"Redirecting to Google authorization URL: {request_uri}")
        return redirect(request_uri)
    except Exception as e:
        logger.error(f"Error in login route: {str(e)}")
        flash("Failed to initialize Google login. Please try again.", "error")
        return redirect(url_for("login"))

@google_auth.route("/google_login/callback")
def callback():
    try:
        logger.debug("Received callback from Google")

        # Verify state parameter
        state = request.args.get('state')
        stored_state = session.pop('oauth_state', None)
        error = request.args.get('error')

        if error:
            logger.error(f"Google OAuth error: {error}")
            flash("Authentication failed: " + error, "error")
            return redirect(url_for("login"))

        logger.debug(f"Received state: {state}")
        logger.debug(f"Stored state: {stored_state}")

        if not state or state != stored_state:
            logger.error("State verification failed")
            flash("Authentication failed: Invalid state parameter.", "error")
            return redirect(url_for("login"))

        code = request.args.get("code")
        if not code:
            logger.error("No authorization code received from Google")
            flash("Authentication failed: No authorization code received.", "error")
            return redirect(url_for("login"))

        google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
        token_endpoint = google_provider_cfg["token_endpoint"]
        redirect_uri = get_redirect_url()

        token_url, headers, body = client.prepare_token_request(
            token_endpoint,
            authorization_response=request.url.replace('http://', 'https://'),
            redirect_url=redirect_uri,
            code=code
        )

        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
        )

        logger.debug(f"Token response status: {token_response.status_code}")

        if not token_response.ok:
            logger.error(f"Token response error: {token_response.text}")
            flash("Authentication failed: Could not get access token.", "error")
            return redirect(url_for("login"))

        client.parse_request_body_response(json.dumps(token_response.json()))

        userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
        uri, headers, body = client.add_token(userinfo_endpoint)
        userinfo_response = requests.get(uri, headers=headers, data=body)

        logger.debug("Processing user info")
        if not userinfo_response.ok:
            logger.error(f"Userinfo response error: {userinfo_response.text}")
            flash("Authentication failed: Could not get user info.", "error")
            return redirect(url_for("login"))

        userinfo = userinfo_response.json()
        if userinfo.get("email_verified"):
            users_email = userinfo["email"]
            users_name = userinfo["given_name"]

            logger.debug(f"User verified: {users_email}")

            user = User.query.filter_by(email=users_email).first()
            if not user:
                logger.debug("Creating new user")
                # Check if username exists and generate a unique one if needed
                base_username = users_name
                username = base_username
                counter = 1
                while User.query.filter_by(username=username).first():
                    username = f"{base_username}{counter}"
                    counter += 1

                user = User(username=username, email=users_email)
                try:
                    db.session.add(user)
                    db.session.commit()
                    logger.debug(f"Created new user with username: {username}")
                except Exception as e:
                    logger.error(f"Error creating user: {str(e)}")
                    db.session.rollback()
                    flash("Failed to create user account. Please try again.", "error")
                    return redirect(url_for("login"))

            # Set session permanent to True and log in user
            session.permanent = True
            login_user(user, remember=True)
            logger.debug("User logged in successfully")

            # Get the next URL from session if available
            next_url = session.pop('next', None)
            if not next_url or not next_url.startswith('/'):
                next_url = url_for('index')

            logger.debug(f"Redirecting to: {next_url}")
            flash("Successfully logged in!", "success")
            return redirect(next_url)
        else:
            logger.error("User email not available or not verified by Google")
            flash("Authentication failed: Email not verified by Google.", "error")
            return redirect(url_for("login"))

    except Exception as e:
        logger.error(f"OAuth error: {str(e)}")
        flash("Authentication failed. Please try again.", "error")
        return redirect(url_for("login"))

@google_auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("login"))