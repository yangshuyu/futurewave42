import re

from marshmallow import fields, ValidationError

from libs.base.schema import BaseSchema


def validate_phone(phone):
    re_phone = re.compile(r'^(100|12[0-9]|13[0-9]|14[5679]|15[0-3,5-9]|16[6]|17[0135678]|18[0-9]|19[89])\d{8}$')
    if re_phone.match(phone):
        return phone
    else:
        raise ValidationError('手机号码格式不正确，请核实', tips='手机号码格式不正确，请核实')


def validate_email(email):
    if 'megvii' in email:
        return email
    else:
        raise ValidationError('邮箱格式不正确，请核实', tips='邮箱格式不正确，请核实')


def validate_password(password):
    if len(password) >= 8:
        return password
    else:
        raise ValidationError('请输入正式格式的密码', tips='请输入正式格式的密码')


class UserSchema(BaseSchema):
    name = fields.Str()
    email = fields.Email()
    phone = fields.Str()
    password = fields.Str(load_only=True)

    class Meta:
        strict = True


class SignupSchema(BaseSchema):
    name = fields.Str(required=True)
    email = fields.Email(required=True, validate=validate_email)
    phone = fields.Str(validate=validate_phone)
    password = fields.Str(required=True, validate=validate_password)

    class Meta:
        strict = True
