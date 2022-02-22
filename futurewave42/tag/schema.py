import re

from marshmallow import fields, ValidationError

from libs.base.schema import BaseSchema


class ChildrenTagSchema(BaseSchema):
    id = fields.Str()
    name = fields.Str()
    sub_id = fields.Str()
    type = fields.Integer()

    class Meta:
        strict = True


class TagSchema(BaseSchema):
    id = fields.Str()
    name = fields.Str(required=True)
    sub_id = fields.Str()
    type = fields.Integer(required=True)
    children = fields.List(fields.Nested(ChildrenTagSchema), dump_only=True)

    class Meta:
        strict = True


class TagPutSchema(BaseSchema):
    name = fields.Str(required=True)
    sub_id = fields.Str()
    type = fields.Integer()

    class Meta:
        strict = True


class TagQuerySchema(BaseSchema):
    page = fields.Int(missing=1)
    per_page = fields.Int(missing=100)
    q = fields.Str()
    type = fields.Integer()

    class Meta:
        strict = True
