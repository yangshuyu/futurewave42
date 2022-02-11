from webargs.flaskparser import use_args

from futurewave42.tag.model import Tag
from futurewave42.tag.schema import TagSchema, TagQuerySchema, TagPutSchema
from libs.auth import jwt_required
from libs.base.resource import BaseResource


class AdminTagsResource(BaseResource):
    # @jwt_required
    @use_args(TagSchema)
    def post(self, args):
        tag = Tag.add(**args)
        data = TagSchema().dump(tag).data
        return data, 201

    @jwt_required
    @use_args(TagQuerySchema)
    def get(self, args):
        tags, total = Tag.get_tags_by_query(**args)
        data = TagSchema(many=True).dump(tags).data
        return self.paginate(
            data, total, args.get('page', 1), args.get('per_page', 100))


class AdminTagResource(BaseResource):
    @jwt_required
    @use_args(TagPutSchema)
    def put(self, args, tag_id):
        tag = Tag.find_by_id(tag_id)
        tag = tag.update(**args)
        data = TagSchema().dump(tag).data
        return data

    # @jwt_required
    # def delete(self, book_id):
    #     book = Book.find_by_id(book_id)
    #     book.delete()
    #     return {}, 204


