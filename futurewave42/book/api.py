import json
import os
import time
import zipfile

from flask import request, send_file
from pygments import BytesIO
from webargs.flaskparser import use_args

from futurewave42.book.model import Book
from futurewave42.book.schema import BookQuerySchema, BookSchema, BookDocsDownloadSchema
from libs.base.resource import BaseResource


class BooksResource(BaseResource):
    @use_args(BookQuerySchema)
    def get(self, args):
        books, total = Book.get_books_by_query(**args)
        data = BookSchema(many=True).dump(books).data
        return self.paginate(
            data, total, args.get('page', 1), args.get('per_page', 10))


class BookResource(BaseResource):
    def get(self, book_id):
        book = Book.find_by_id(book_id)
        data = BookSchema().dump(book).data
        return data


class BookDocsDownloadResource(BaseResource):
    @use_args(BookDocsDownloadSchema)
    def get(self, args):
        docs = args.get('docs')
        docs = json.loads(docs)
        memory_file = BytesIO()
        print("+++++++++++++++++++++++")
        with zipfile.ZipFile(memory_file, 'w') as zf:
            for doc in docs:
                path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../files/'))
                with open('{}/{}'.format(path, doc), 'rb') as fp:
                    zf.writestr(doc, fp.read())
        memory_file.seek(0)
        return send_file(memory_file,
                         mimetype='zip',
                         attachment_filename='docs.zip',
                         as_attachment=True)

