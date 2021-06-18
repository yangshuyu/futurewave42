import re

from marshmallow import fields, ValidationError

from libs.base.schema import BaseSchema


class VideoSchema(BaseSchema):
    id = fields.Str()
    name = fields.Str()
    image = fields.Str(required=True)
    title = fields.Str(required=True)
    video = fields.Str(required=True)
    context = fields.Str(required=True)
    doc = fields.Str()
    cover = fields.Str(dump_only=True)

    class Meta:
        strict = True


class VideoPutSchema(BaseSchema):
    name = fields.Str()
    image = fields.Str()
    title = fields.Str()
    video = fields.Str()
    context = fields.Str()
    doc = fields.Str()

    class Meta:
        strict = True


class VideoQuerySchema(BaseSchema):
    page = fields.Int(missing=1)
    per_page = fields.Int(missing=20)

    class Meta:
        strict = True
