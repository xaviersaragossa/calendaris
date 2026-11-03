import json
import os
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

import db

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]
fernet = Fernet(os.environ["TOKEN_KEY"].encode())

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/calendar.readonly",  # canvia a .../auth/calendar per poder editar
]
REDIRECT_URI = os.environ.get("REDIRECT_URI", "http://localhost:5000/callback")

db.init()


def make_flow():
    config = {
        "web": {
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    return Flow.from_client_config(config, scopes=SCOPES, redirect_uri=REDIRECT_URI)


def encrypt(text):
    return fernet.encrypt(text.encode()).decode()


def decrypt(text):
    return fernet.decrypt(text.encode()).decode()


def current_user():
    gid = session.get("google_id")
    return db.get_user(gid) if gid else None


def fmt_when(start):
    """Converteix l'inici d'un esdeveniment de Google en text llegible."""
    if "dateTime" in start:
        dt = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    d = datetime.fromisoformat(start["date"])
    return d.strftime("%d/%m/%Y") + " (tot el dia)"


@app.route("/")
def index():
    if current_user():
        return redirect(url_for("calendaris"))
    return render_template("login.html")


@app.route("/login")
def login():
    flow = make_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",  # per obtenir refresh token
        prompt="consent",
        include_granted_scopes="true",
    )
    session["state"] = state
    session["code_verifier"] = flow.code_verifier
    return redirect(auth_url)


@app.route("/callback")
def callback():
    if request.args.get("state") != session.get("state"):
        return "Estat OAuth invàlid", 400
    if "error" in request.args:
        return render_template("login.html", error="Has cancel·lat l'accés o Google l'ha denegat.")

    flow = make_flow()
    flow.code_verifier = session.get("code_verifier")
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials

    info = build("oauth2", "v2", credentials=creds).userinfo().get().execute()
    gid = info["id"]

    # Si Google no retorna refresh_token, conservem el que ja teníem
    token_data = json.loads(creds.to_json())
    if not token_data.get("refresh_token"):
        old = db.get_user(gid)
        if old:
            token_data["refresh_token"] = json.loads(decrypt(old["token"])).get("refresh_token")

    db.save_user(gid, info["email"], info.get("name"), encrypt(json.dumps(token_data)))
    session["google_id"] = gid
    return redirect(url_for("calendaris"))


@app.route("/calendaris")
def calendaris():
    user = current_user()
    if not user:
        return redirect(url_for("index"))

    creds = Credentials.from_authorized_user_info(json.loads(decrypt(user["token"])), SCOPES)
    try:
        service = build("calendar", "v3", credentials=creds)
        llista = service.calendarList().list().execute().get("items", [])

        cal_id = request.args.get("id") or next(
            (c["id"] for c in llista if c.get("primary")), "primary"
        )
        ara = datetime.now(timezone.utc).isoformat()
        events = (
            service.events()
            .list(calendarId=cal_id, timeMin=ara, maxResults=15,
                  singleEvents=True, orderBy="startTime")
            .execute()
            .get("items", [])
        )
    except RefreshError:
        # El token ja no és vàlid (l'usuari ha revocat l'accés, etc.)
        session.clear()
        return redirect(url_for("login"))

    # Desem el token per si s'ha renovat durant les crides
    db.update_token(user["google_id"], encrypt(creds.to_json()))

    for e in events:
        e["quan"] = fmt_when(e["start"])
    return render_template("calendaris.html", user=user, calendaris=llista,
                           actiu=cal_id, events=events)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
