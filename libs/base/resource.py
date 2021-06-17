import jwt

from flask import request
from flask_restful import Resource

from futurewave42.account import User


class BaseResource(Resource):
    record = None

    # @classmethod
    # def check_record(cls, model, model_key, model_message=None):
    #     def decorate(func):
    #         @wraps(func)
    #         def wrapper(*args, **kwargs):
    #             record_id = kwargs.get(model_key)
    #             message = model_message if model_message else str(model)
    #             record = model.find_by_id(record_id)
    #             if record is None:
    #                 error(InterfaceTips.DATA_NOT_EXISTED)
    #             cls.record = record
    #             return func(*args, **kwargs)
    #         return wrapper
    #     return decorate
    #
    @property
    def current_user(self):
        from config import load_config

        config = load_config()
        cookie = request.headers.get("X-Token")

        if not cookie:
            return None
        try:
            data = jwt.decode(
                cookie,
                config.SECRET_KEY,
                audience=config.AUDIENCE,
                algorithms=["HS256"],
            )
            user_id = data.get("user_id")
            return User.find_by_id(user_id)
        except Exception as e:
            print(e)

    def paginate(self, result, total, page=1, per_page=10):
        has_more = page * per_page < total
        return (
            result,
            200,
            {
                "_extra_data": {"has_more": has_more},
                "X-Total": total,
                "X-Per-Page": per_page,
            },
        )


def generate_response(data, code=0, message='成功'):
    return data, 200, {'message': message, 'response_code': code}
