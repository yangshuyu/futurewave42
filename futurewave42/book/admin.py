import os

from flask import request
from webargs.flaskparser import use_args

from futurewave42.book.model import Book
from futurewave42.book.schema import BookSchema, BookPutSchema, BookQuerySchema
from libs.auth import jwt_required
from libs.base.resource import BaseResource


class AdminBooksResource(BaseResource):
    # @jwt_required
    @use_args(BookSchema)
    def post(self, args):
        book = Book.add(**args)
        data = BookSchema().dump(book).data
        return data, 201

    @jwt_required
    @use_args(BookQuerySchema)
    def get(self, args):
        books, total = Book.get_books_by_query(**args)
        data = BookSchema(many=True).dump(books).data
        return self.paginate(
            data, total, args.get('page', 1), args.get('per_page', 10))


class AdminBookResource(BaseResource):
    @jwt_required
    @use_args(BookPutSchema)
    def put(self, args, book_id):
        book = Book.find_by_id(book_id)
        book = book.update(**args)
        data = BookSchema().dump(book).data
        return data

    @jwt_required
    def delete(self, book_id):
        book = Book.find_by_id(book_id)
        book.delete()
        return {}, 204


class AdminFileResource(BaseResource):
    @jwt_required
    def post(self):
        files = request.files
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../files/'))
        data = []
        for f in files:
            file = files.get(f)
            filename = file.filename
            data.append(filename)
            file.save(os.path.join(path, filename))
        return data

