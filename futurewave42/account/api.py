from flask import request
from webargs.flaskparser import use_args

from libs.auth import OAuth, jwt_required
from libs.base.resource import BaseResource
from futurewave42.account import User
from futurewave42.account.schema import UserSchema, SignupSchema
from libs.error import dynamic_error


class SignupResource(BaseResource):
    @use_args(SignupSchema())
    def post(self, args):
        u = User.add(**args)
        data = UserSchema().dump(u).data
        return data, 201


class LoginResource(BaseResource):
    @use_args(UserSchema())
    def post(self, args):
        email, password = args.get("email"), args.get("password")

        if not email or not password:
            dynamic_error({}, code=422, message='请输入正确的用户名或密码')
        u = User.get_user_by_email(email=email, password=password)
        if not u:
            dynamic_error({}, code=422, message='用户或密码错误')
        data = UserSchema().dump(u).data
        data["access_token"] = OAuth().create_token(u)
        return data

    def get(self):
        return {'code': 40010020, 'data': {}, 'msg': '不支持此方法'}


class LogoutResource(BaseResource):
    @jwt_required
    # @requires(POST, 'logout')
    def post(self):
        print(self.current_user)
        # revoke_token()
        return {}


class Callback(BaseResource):
    def get(self):
        args = request.args
        return OAuth().callback(**args)
