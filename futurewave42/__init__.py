#!/usr/bin/python
# -*- coding: UTF-8 -*-
from flask import Blueprint

from futurewave42.account.api import LoginResource, LogoutResource, SignupResource, Callback
from futurewave42.api import CustomApi
from futurewave42.author.admin import AdminAuthorsResource, AdminAuthorResource
from futurewave42.author.api import AuthorsResource, AuthorResource
from futurewave42.book.admin import AdminBooksResource, AdminBookResource, AdminFileResource
from futurewave42.book.api import BooksResource, BookResource, BookDocsDownloadResource
from futurewave42.configuration.admin import AdminLastConfigurationResource, AdminConfigurationResource
from futurewave42.configuration.api import LastConfigurationResource
from futurewave42.tag.admin import AdminTagsResource, AdminTagResource
from futurewave42.tag.api import TagsResource
from futurewave42.video.admin import AdminVideosResource, AdminVideoResource
from futurewave42.video.api import VideosResource, VideoResource

'''
    api的url同意注册口
'''

api_bp_v1 = Blueprint('api_v1', __name__)
api_v1 = CustomApi(api_bp_v1, prefix='/api/v1')

#user
api_v1.add_resource(SignupResource, '/signup')
api_v1.add_resource(LoginResource, '/login')
api_v1.add_resource(LogoutResource, '/logout')
api_v1.add_resource(Callback, '/callback')

api_v1.add_resource(BooksResource, '/books')
api_v1.add_resource(BookResource, '/books/<book_id>')
api_v1.add_resource(BookDocsDownloadResource, "/books/docs")

api_v1.add_resource(AdminBooksResource, '/admin/books')
api_v1.add_resource(AdminBookResource, '/admin/books/<book_id>')
api_v1.add_resource(AdminFileResource, '/admin/files')

api_v1.add_resource(LastConfigurationResource, '/last/configuration')

api_v1.add_resource(AdminLastConfigurationResource, '/admin/last/configuration')
api_v1.add_resource(AdminConfigurationResource, '/admin/configuration/<configuration_id>')


api_v1.add_resource(VideosResource, '/videos')
api_v1.add_resource(VideoResource, '/videos/<video_id>')
api_v1.add_resource(AdminVideosResource, '/admin/videos')
api_v1.add_resource(AdminVideoResource, '/admin/videos/<video_id>')


api_v1.add_resource(AdminTagsResource, '/admin/tags')
api_v1.add_resource(AdminTagResource, '/admin/tags/<tag_id>')
api_v1.add_resource(TagsResource, '/tags')


api_v1.add_resource(AdminAuthorsResource, '/admin/authors')
api_v1.add_resource(AdminAuthorResource, '/admin/authors/<author_id>')
api_v1.add_resource(AuthorsResource, '/authors')
api_v1.add_resource(AuthorResource, '/authors/<author_id>')


BLUEPRINTS = [
    api_bp_v1
]

__all__ = ['BLUEPRINTS']
