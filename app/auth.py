import datetime

import bcrypt
import jwt
from flask import request

from config import SECRET_KEY


def verify_password(password, stored_hash):
    return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))


def generate_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token


def verify_token():
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return None, {"error": "Authorization header missing"}, 401

    try:
        token = auth_header.split(" ")[1]
    except IndexError:
        return None, {"error": "Invalid Authorization header"}, 401

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload["user_id"]
        return user_id, None, None
    except jwt.ExpiredSignatureError:
        return None, {"error": "Token expired"}, 401
    except jwt.InvalidTokenError:
        return None, {"error": "Invalid token"}, 401
