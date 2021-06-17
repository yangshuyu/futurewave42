import re

from marshmallow import fields, ValidationError

from libs.base.schema import BaseSchema


class ConfigurationSchema(BaseSchema):
    id = fields.Str()
    contact = fields.Str(required=True)
    home = fields.Str(required=True)
    company = fields.Str(required=True)

    class Meta:
        strict = True


class ConfigurationPutSchema(BaseSchema):
    id = fields.Str()
    contact = fields.Str()
    home = fields.Str()
    company = fields.Str()

    class Meta:
        strict = True
