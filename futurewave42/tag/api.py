import os
import time
import zipfile

from flask import request, send_file
from pygments import BytesIO
from webargs.flaskparser import use_args

from futurewave42.tag.model import Tag
from futurewave42.tag.schema import TagQuerySchema, TagSchema
from libs.base.resource import BaseResource


class TagsResource(BaseResource):
    @use_args(TagQuerySchema)
    def get(self, args):
        tags, total = Tag.get_tags_by_query(**args)
        data = TagSchema(many=True).dump(tags).data
        return self.paginate(
            data, total, args.get('page', 1), args.get('per_page', 100))

