import datetime

from sqlalchemy import or_
from sqlalchemy.dialects.postgresql import UUID, JSONB

from config import load_config
from futurewave42.ext import db
from libs.base.model import BaseModel, QueryWithSoftDelete
from libs.error import dynamic_error


class Author(BaseModel):
    __tablename__ = 'authors'

    avatar = db.Column(db.String, nullable=False)
    e_name = db.Column(db.String(512), default='')
    c_name = db.Column(db.String(512), default='')
    introduction = db.Column(db.String)
    deleted_at = db.Column(db.DateTime, index=True)

    query_class = QueryWithSoftDelete

    @property
    def cover(self):
        return '{}{}'.format(load_config().CDN_DOMAIN, self.avatar)

    def delete(self):
        self.deleted_at = datetime.datetime.now()
        db.session.commit()

    def update(self, **kwargs):
        try:
            for k, v in kwargs.items():
                if hasattr(self, k):
                    setattr(self, k, v)

            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

        return self

    @classmethod
    def add(cls, **kwargs):
        author = cls(
            avatar=kwargs.get('avatar'),
            e_name=kwargs.get('e_name'),
            c_name=kwargs.get('c_name'),
            introduction=kwargs.get('introduction'),
        )
        db.session.add(author)

        try:
            db.session.commit()
        except Exception as e:
            print(e)
            db.session.rollback()
            dynamic_error({}, code=422, message=str(e))
        return author

    @classmethod
    def get_authors_by_query(cls, **kwargs):
        page = kwargs.get('page')
        per_page = kwargs.get('per_page')
        q = kwargs.get('q')
        query = cls.query

        if q:
            query = query.filter(or_(
                cls.e_name.ilike("%{}%".format(q)),
                cls.c_name.ilike("%{}%".format(q)),
            ))
        query = query.order_by(cls.created_at.desc())
        total = cls.get_count(query)

        if page and per_page:
            query = query.limit(per_page).offset((page - 1) * per_page)
        return query.all(), total
