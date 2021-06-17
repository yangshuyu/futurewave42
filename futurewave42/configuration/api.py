from flask import request
from webargs.flaskparser import use_args

from futurewave42.book.model import Book
from futurewave42.book.schema import BookQuerySchema, BookSchema
from futurewave42.configuration.model import Configuration
from futurewave42.configuration.schema import ConfigurationSchema
from libs.base.resource import BaseResource


class LastConfigurationResource(BaseResource):
    def get(self):
        c = Configuration.get_last_configuration()
        data = ConfigurationSchema().dump(c).data
        return data

