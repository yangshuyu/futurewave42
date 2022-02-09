import re

from marshmallow import fields, ValidationError

from libs.base.schema import BaseSchema


class BookSchema(BaseSchema):
    id = fields.Str()
    name = fields.Str(required=True)
    author = fields.Str(required=True)
    language = fields.Str(required=True)
    image = fields.Str(required=True)
    title = fields.Str(required=True)
    images = fields.List(fields.Str(), missing=[])
    context = fields.Str(required=True)
    doc = fields.Str()
    docs = fields.List(fields.Str(), missing=[])
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

    class Meta:
        strict = True


class BookQuerySchema(BaseSchema):
    page = fields.Int(missing=1)
    per_page = fields.Int(missing=10)
    q = fields.Str()

    class Meta:
        strict = True


class BookDocsDownloadSchema(BaseSchema):
    docs = fields.List(fields.Str(), missing=[])

    class Meta:
        strict = True
