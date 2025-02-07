import json
import os
import logging
import requests
from extensions import db
from flask import Blueprint, redirect, request, url_for, session
from flask_login import login_required, login_user, logout_user
from models import User
from oauthlib.oauth2 import WebApplicationClient
import secrets

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

GOOGLE_CLIENT_ID = os.environ["GOOGLE_OAUTH_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_OAUTH_CLIENT_SECRET"]
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Make sure to use this redirect URL. It has to match the one in the whitelist
REPLIT_DOMAIN = os.environ.get("REPLIT_DEV_DOMAIN")
if not REPLIT_DOMAIN:
    raise ValueError("REPLIT_DEV_DOMAIN environment variable is not set")

DEV_REDIRECT_URL = f'https://{REPLIT_DOMAIN}/google_login/callback'

print(f"""To make Google authentication work:
1. Go to https://console.cloud.google.com/apis/credentials
2. Create a new OAuth 2.0 Client ID
3. Add {DEV_REDIRECT_URL} to Authorized redirect URIs

For detailed instructions, see:
https://docs.replit.com/additional-resources/google-auth-in-flask#set-up-your-oauth-app--client
""")

client = WebApplicationClient(GOOGLE_CLIENT_ID)

google_auth = Blueprint("google_auth", __name__)

@google_auth.route("/google_login")
def login():
    try:
        logger.debug("Starting Google login process")

        # Generate and store a random state parameter
        session['oauth_state'] = secrets.token_urlsafe(32)

        google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
        authorization_endpoint = google_provider_cfg["authorization_endpoint"]

        logger.debug(f"Using redirect URL: {DEV_REDIRECT_URL}")
        request_uri = client.prepare_request_uri(
            authorization_endpoint,
            redirect_uri=DEV_REDIRECT_URL,
            scope=["openid", "email", "profile"],
            state=session['oauth_state']
        )
        logger.debug(f"Redirecting to Google authorization URL: {request_uri}")
        return redirect(request_uri)
    except Exception as e:
        logger.error(f"Error in login route: {str(e)}")
        return redirect(url_for("index"))

@google_auth.route("/google_login/callback")
def callback():
    try:
        logger.debug("Received callback from Google")
        logger.debug(f"Request URL: {request.url}")
        logger.debug(f"Request args: {request.args}")

        # Verify state parameter
        state = request.args.get('state')
        stored_state = session.pop('oauth_state', None)

        logger.debug(f"Received state: {state}")
        logger.debug(f"Stored state: {stored_state}")

        if not state or state != stored_state:
            logger.error("State verification failed")
            return redirect(url_for("index"))

        code = request.args.get("code")
        if not code:
            logger.error("No authorization code received from Google")
            return redirect(url_for("index"))

        google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
        token_endpoint = google_provider_cfg["token_endpoint"]

        logger.debug("Preparing token request")
        token_url, headers, body = client.prepare_token_request(
            token_endpoint,
            authorization_response=request.url,
            redirect_url=DEV_REDIRECT_URL,
            code=code
        )

        logger.debug(f"Token request URL: {token_url}")
        logger.debug(f"Token request headers: {headers}")
        logger.debug(f"Token request body: {body}")

        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
        )

        logger.debug(f"Token response status: {token_response.status_code}")

        if not token_response.ok:
            logger.error(f"Token response error: {token_response.text}")
            return redirect(url_for("index"))

        client.parse_request_body_response(json.dumps(token_response.json()))

        userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
        uri, headers, body = client.add_token(userinfo_endpoint)
        userinfo_response = requests.get(uri, headers=headers, data=body)

        logger.debug("Processing user info")
        if not userinfo_response.ok:
            logger.error(f"Userinfo response error: {userinfo_response.text}")
            return redirect(url_for("index"))

        userinfo = userinfo_response.json()
        if userinfo.get("email_verified"):
            users_email = userinfo["email"]
            users_name = userinfo["given_name"]

            logger.debug(f"User verified: {users_email}")

            user = User.query.filter_by(email=users_email).first()
            if not user:
                logger.debug("Creating new user")
                user = User(username=users_name, email=users_email)
                db.session.add(user)
                db.session.commit()

            login_user(user)
            logger.debug("User logged in successfully")
            return redirect(url_for("index"))
        else:
            logger.error("User email not verified by Google")
            return "User email not available or not verified by Google.", 400

    except Exception as e:
        logger.error(f"OAuth error: {str(e)}")
        return redirect(url_for("index"))

@google_auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))