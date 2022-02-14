from webargs.flaskparser import use_args

from futurewave42.author.model import Author
from futurewave42.author.schema import AuthorSchema, AuthorQuerySchema, AuthorPutSchema
from libs.auth import jwt_required
from libs.base.resource import BaseResource


class AdminAuthorsResource(BaseResource):
    # @jwt_required
    @use_args(AuthorSchema)
    def post(self, args):
        author = Author.add(**args)
        data = AuthorSchema().dump(author).data
        return data, 201

    # @jwt_required
    @use_args(AuthorQuerySchema)
    def get(self, args):
        authors, total = Author.get_authors_by_query(**args)
        data = AuthorSchema(many=True).dump(authors).data
        return self.paginate(
            data, total, args.get('page', 1), args.get('per_page', 100))


class AdminAuthorResource(BaseResource):
    # @jwt_required
    @use_args(AuthorPutSchema)
    def put(self, args, author_id):
        author = Author.find_by_id(author_id)
        author = author.update(**args)
        data = AuthorSchema().dump(author).data
        return data

    @jwt_required
    def delete(self, book_id):
        author = Author.find_by_id(book_id)
        author.delete()
        return {}, 204


