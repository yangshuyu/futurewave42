import os
import time
import zipfile

from flask import request, send_file
from pygments import BytesIO
from webargs.flaskparser import use_args

from futurewave42.author.model import Author
from futurewave42.author.schema import AuthorQuerySchema, AuthorSchema
from libs.base.resource import BaseResource


class AuthorsResource(BaseResource):
    @use_args(AuthorQuerySchema)
    def get(self, args):
        authors, total = Author.get_authors_by_query(**args)
        data = AuthorSchema(many=True).dump(authors).data
        return self.paginate(
            data, total, args.get('page', 1), args.get('per_page', 100))

