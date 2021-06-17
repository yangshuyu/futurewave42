#!/usr/bin/python
# -*- coding: UTF-8 -*-
from flask import Blueprint

from futurewave42.account.api import LoginResource, LogoutResource, SignupResource, Callback
from futurewave42.api import CustomApi
from futurewave42.book.admin import AdminBooksResource, AdminBookResource, AdminFileResource
from futurewave42.book.api import BooksResource, BookResource
from futurewave42.configuration.admin import AdminLastConfigurationResource, AdminConfigurationResource
from futurewave42.configuration.api import LastConfigurationResource

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

api_v1.add_resource(AdminBooksResource, '/admin/books')
api_v1.add_resource(AdminBookResource, '/admin/books/<book_id>')
api_v1.add_resource(AdminFileResource, '/admin/files')

api_v1.add_resource(LastConfigurationResource, '/last/configuration')

api_v1.add_resource(AdminLastConfigurationResource, '/admin/last/configuration')
api_v1.add_resource(AdminConfigurationResource, '/admin/configuration/<configuration_id>')



BLUEPRINTS = [
    api_bp_v1
]

__all__ = ['BLUEPRINTS']
