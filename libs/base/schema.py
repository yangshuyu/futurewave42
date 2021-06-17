import arrow
from marshmallow import Schema, fields, post_dump


class BaseSchema(Schema):
    @post_dump
    def clear_none(self, data):
        result = {}
        for k, v in data.items():
            if v is None:
                continue
            elif isinstance(v, dict):
                result[k] = self.clear_none(v)
            else:
                result[k] = v
        return result


class BaseQuerySchema(BaseSchema):
    page = fields.Int(
        missing=1, location="query", validate=lambda val: 1000 > val > 0
    )
    per_page = fields.Int(
        missing=20, location="query", validate=lambda val: 2000 > val > 0
    )
    q = fields.Str(location="query")
    original = fields.Int(missing=-1, location="query")
    source = fields.Str(location="query")

    class Meta:
        strict = True


class Base64Uri(fields.String):
    def _serialize(self, value, attr, obj):
        if value is None:
            return

        return value + "yangshuyu"

    def _deserialize(self, value, attr, data):
        if value is None:
            return

        with open("/Users/yangshuyu/job/orange.png", "rb") as f:
            import base64

            base64_data = base64.b64encode(f.read())
            s = base64_data.decode()
            return "data:image/png;base64,%s" % s


class Timestamp(fields.Integer):
    def _serialize(self, value, attr, obj):
        if value:
            return str(arrow.get(value).datetime)[0:19]

    def _deserialize(self, value, attr, obj):
        return arrow.get(value).datetime
