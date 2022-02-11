import re

from marshmallow import fields, ValidationError

from libs.base.schema import BaseSchema


class ChildrenTagSchema(BaseSchema):
    id = fields.Str()
    name = fields.Str()
    sub_id = fields.Str()

    class Meta:
        strict = True


class TagSchema(BaseSchema):
    id = fields.Str()
    name = fields.Str(required=True)
    sub_id = fields.Str()
    children = fields.List(fields.Nested(ChildrenTagSchema), dump_only=True)

    class Meta:
        strict = True


class TagPutSchema(BaseSchema):
    name = fields.Str(required=True)
    sub_id = fields.Str()

    class Meta:
        strict = True


class TagQuerySchema(BaseSchema):
    page = fields.Int(missing=1)
    per_page = fields.Int(missing=100)
    q = fields.Str()

    class Meta:
        strict = True
