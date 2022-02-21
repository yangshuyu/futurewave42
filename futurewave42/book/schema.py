import re

from marshmallow import fields, ValidationError

from futurewave42.author.schema import AuthorSchema
from futurewave42.tag.schema import TagSchema
from libs.base.schema import BaseSchema


class BookSchema(BaseSchema):
    id = fields.Str()
    name = fields.Str(required=True)
    author = fields.Str()
    language = fields.Str(required=True)
    image = fields.Str(required=True)
    title = fields.Str(required=True)
    images = fields.List(fields.Str(), missing=[])
    context = fields.Str(required=True)
    doc = fields.Str()
    docs = fields.List(fields.Str(), missing=[])
    tag_ids = fields.Str()
    author_id = fields.Str()

    tags = fields.List(fields.Nested(TagSchema), dump_only=True)
    new_author = fields.Nested(AuthorSchema, dump_only=True)

    cover = fields.Str(dump_only=True)
    detail_images = fields.List(fields.Str(), missing=[], dump_only=True)

    class Meta:
        strict = True


class BookPutSchema(BaseSchema):
    name = fields.Str()
    author = fields.Str()
    language = fields.Str()
    image = fields.Str()
    title = fields.Str()
    images = fields.List(fields.Str(), missing=[])
    context = fields.Str()
    doc = fields.Str()
    docs = fields.List(fields.Str(), missing=[])
    tag_ids = fields.List(fields.Str())
    author_id = fields.Str()

    class Meta:
        strict = True


class BookQuerySchema(BaseSchema):
    page = fields.Int(missing=1)
    per_page = fields.Int(missing=10)
    tag_id = fields.Str()
    author_id = fields.Str()
    q = fields.Str()

    class Meta:
        strict = True


class BookDocsDownloadSchema(BaseSchema):
    docs = fields.Str()

    class Meta:
        strict = True
