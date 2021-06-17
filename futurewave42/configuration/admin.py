from futurewave42.configuration.model import Configuration
from futurewave42.configuration.schema import ConfigurationSchema, ConfigurationPutSchema
from libs.base.resource import BaseResource
from webargs.flaskparser import use_args


class AdminLastConfigurationResource(BaseResource):
    def get(self):
        c = Configuration.get_last_configuration()
        data = ConfigurationSchema().dump(c).data
        return data


class AdminConfigurationResource(BaseResource):
    @use_args(ConfigurationPutSchema)
    def put(self, args, configuration_id):
        c = Configuration.find_by_id(configuration_id)
        c.update(**args)
        data = ConfigurationSchema().dump(c).data
        return data
