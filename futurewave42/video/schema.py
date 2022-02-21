import re

from marshmallow import fields, ValidationError

from futurewave42.author.schema import AuthorSchema
from futurewave42.tag.schema import TagSchema
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

    tag_ids = fields.Str()
    author_id = fields.Str()

    tags = fields.List(fields.Nested(TagSchema), dump_only=True)
    new_author = fields.Nested(AuthorSchema, dump_only=True)

    class Meta:
        strict = True


class VideoPutSchema(BaseSchema):
    name = fields.Str()
    image = fields.Str()
    title = fields.Str()
    video = fields.Str()
    context = fields.Str()
    doc = fields.Str()
    tag_ids = fields.List(fields.Str())
    author_id = fields.Str()

    class Meta:
        strict = True


class VideoQuerySchema(BaseSchema):
    page = fields.Int(missing=1)
    per_page = fields.Int(missing=20)
    tag_id = fields.Str()
    author_id = fields.Str()
    q = fields.Str()

    class Meta:
        strict = True
