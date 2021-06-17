from flask import request
from webargs.flaskparser import use_args

from futurewave42.book.model import Book
from futurewave42.book.schema import BookQuerySchema, BookSchema
from libs.base.resource import BaseResource


class BooksResource(BaseResource):
    @use_args(BookQuerySchema)
    def get(self, args):
        books, total = Book.get_books_by_query(**args)
        data = BookSchema(many=True).dump(books).data
        return self.paginate(
            data, total, args.get('page', 1), args.get('per_page', 10))
