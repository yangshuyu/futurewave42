import re

from marshmallow import fields, ValidationError

from libs.base.schema import BaseSchema


class AuthorSchema(BaseSchema):
    id = fields.Str()
    avatar = fields.Str(required=True)
    e_name = fields.Str()
    c_name = fields.Str()
    introduction = fields.Str(required=True)
    cover = fields.Str(dump_only=True)

    class Meta:
        strict = True


class AuthorPutSchema(BaseSchema):
    avatar = fields.Str(required=True)
    e_name = fields.Str()
    c_name = fields.Str()
    introduction = fields.Str(required=True)

    class Meta:
        strict = True


class AuthorQuerySchema(BaseSchema):
    page = fields.Int(missing=1)
    per_page = fields.Int(missing=100)
    q = fields.Str()

    class Meta:
        strict = True
