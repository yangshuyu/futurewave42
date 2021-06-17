from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm.attributes import flag_modified
from config import load_config
from futurewave42.ext import db
from libs.base.model import BaseModel
from libs.error import dynamic_error


class Configuration(BaseModel):
    __tablename__ = 'configurations'

    home = db.Column(db.String, nullable=False)
    company = db.Column(db.String, nullable=False)
    contact = db.Column(db.String, nullable=False)

    @classmethod
    def get_last_configuration(cls):
        c = cls.query.first()
        return c
