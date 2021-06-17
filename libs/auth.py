import requests
import jwt
import arrow

from functools import wraps
from urllib.parse import urlencode
from flask import request
from sqlalchemy import and_

from config import load_config
from werkzeug.utils import redirect

from futurewave42.account.model import Role, UserRole
from libs.constants import RoleType
from libs.error import error
from futurewave42.account import User
from libs.interface_tips import InterfaceTips

config = load_config()


class OAuth(object):
    """
    First redirect /authorize Megvii OAuth2 URL is a web.
    then input username and password
    Then  Megvii will redirect to /callback of mine given
    a temp code. then fetch TOKEN by temp code
    Second fetch user info through TOKEN

    """

    def create_token(self, user):
        payload = {
            "iss": "futurewave42",
            "iat": arrow.now().timestamp,
            "exp": arrow.now().shift(days=30).timestamp,
            "aud": "megvii",
            "sub": "Delivery center management system",
            "username": user.name,
            "user_id": user.id,
        }
        token = jwt.encode(payload, config.SECRET_KEY, algorithm="HS256").decode(
            "utf-8"
        )
        return token

    def get_user_info(self, token):
        body = dict(token=token)
        resp = requests.post(
            "{}/get_info".format("https://sso.megvii-inc.com/cas/oauth2"), data=body
        )
        if resp.status_code != 200:
            print(resp)
        return resp.json()

    def login(self):
        payload = dict(
            client_id=config.CLIENT_ID,
            redirect_uri="{}://{}/api/v1/callback".format(
                config.SERVER_SCHEME, config.SERVER_DOMAIN
            ),
            response_type="code",
            _time=arrow.now().timestamp,
        )
        return "{}/authorize?{}".format(
            "https://sso.megvii-inc.com/cas/oauth2", urlencode(payload)
        )

    def callback(self, code):
        """
        Get username through token. then add username into
        cookie and redirect `current_url`
        """
        body = dict(
            code=code,
            client_id=config.CLIENT_ID,
            client_secret=config.CLIENT_SECRET,
            redirect_uri="{}://{}/api/v1/callback".format(
                config.SERVER_SCHEME, config.SERVER_DOMAIN
            ),
            grant_type="authorization_code",
        )
        resp = requests.post(
            "{}/token".format("https://sso.megvii-inc.com/cas/oauth2"),
            data=body
        )
        if resp.status_code != 200:
            print("/token, request: {}, response: {}".format(body, resp.status_code))
        content = resp.json()

        auth_user = self.get_user_info(token=content["access_token"])
        user = User.get_user_by_email(email=auth_user.get("email"))
        if not user:
            kwargs = {"name": auth_user.get("id"), "email": auth_user.get("email")}
            user = User.add(**kwargs)
            role = Role.query.filter(Role.type == RoleType.General.value).first()
            ur_kwargs = {'user_id': user.id, 'role_id': role.id}
            UserRole.add(**ur_kwargs)

        # 重定向的url
        response = redirect("{}://{}/#/".format(config.SERVER_SCHEME, config.SERVER_DOMAIN))
        response.set_cookie(
            "futurewave42-login",
            self.create_token(user=user),
            expires=arrow.now().shift(days=10).datetime,
        )
        response.set_cookie(
            "user-id", user.id, expires=arrow.now().shift(days=10).datetime
        )
        response.set_cookie(
            "user_email",
            user.email,
            expires=arrow.now().shift(days=10).datetime
        )
        response.set_cookie(
            "role",
            ','.join([str(ur.type) for ur in user.roles]),
            expires=arrow.now().shift(days=10).datetime
        )
        return response


def jwt_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        cookie = request.headers.get("X-Token")
        if not cookie:
            error(InterfaceTips.MISSING_TOKEN)
        try:
            jwt.decode(
                cookie,
                config.SECRET_KEY,
                audience=config.AUDIENCE,
                algorithms=["HS256"],
            )
        except Exception as e:
            print(e)
            error(InterfaceTips.EXPIRED_TOKEN)
        return func(*args, **kwargs)

    return wrapper


def get_login_user_msg():
    cookie = request.headers.get("X-Token")
    if cookie:
        user_msg = jwt.decode(
            cookie,
            config.SECRET_KEY,
            audience=config.AUDIENCE,
            algorithms=["HS256"],
        )
        return user_msg
