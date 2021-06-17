import datetime

import uuid

from flask_sqlalchemy import BaseQuery
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
from futurewave42.ext import db


class BaseModel(db.Model):
    __abstract__ = True

    id = db.Column(UUID, default=lambda: str(uuid.uuid4()), primary_key=True)

    created_at = db.Column(db.DateTime, default=datetime.datetime.now,
                           index=True)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.datetime.now,
        onupdate=datetime.datetime.now,
        index=True,
    )

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__, self.id)

    @classmethod
    def find_by_id(cls, _id):
        return cls.query.filter(cls.id == _id).first()

    @classmethod
    def find_by_ids(cls, _ids):
        if not _ids:
            return []
        return cls.query.filter(cls.id.in_(_ids)).all()

    @classmethod
    def add(cls, **kwargs):
        auto_commit = kwargs.pop("auto_commit", True)
        obj = cls(**kwargs)
        db.session.add(obj)
        try:
            if auto_commit:
                db.session.commit()
        except Exception as e:
            print(e)
            db.session.rollback()
            raise

        return obj

    @classmethod
    def get_count(cls, q):
        count_q = q.statement.with_only_columns([func.count()]).order_by(None)
        count = q.session.execute(count_q).scalar()
        return count

    def update(self, **kwargs):
        auto_commit = kwargs.pop("auto_commit", True)
        try:
            for k, v in kwargs.items():
                if hasattr(self, k):
                    setattr(self, k, v)

            self.updated_at = datetime.datetime.now()
            db.session.add(self)

            if auto_commit:
                print(datetime.datetime.now())
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

        return self

    @classmethod
    def get_all(cls):
        return cls.query.all()

    def delete(self, auto_commit=True):
        db.session.delete(self)
        if auto_commit:
            db.session.commit()

    def to_json(self):
        return {c.key: getattr(self, c.key, None)
                for c in self.__class__.__table__.columns}


class QueryWithSoftDelete(BaseQuery):
    def __new__(cls, *args, **kwargs):
        obj = super(QueryWithSoftDelete, cls).__new__(cls)
        with_deleted = kwargs.pop("_with_deleted", False)
        if len(args) > 0:
            super(QueryWithSoftDelete, obj).__init__(*args, **kwargs)
            return obj.filter_by(deleted_at=None) if not with_deleted else obj
        return obj

    def __init__(self, *args, **kwargs):
        pass

    def with_deleted(self):
        return self.__class__(
            db.class_mapper(self._mapper_zero().class_),
            session=db.session(),
            _with_deleted=True,
        )

    def _get(self, *args, **kwargs):
        # this calls the original query.get function from the base class
        return super(QueryWithSoftDelete, self).get(*args, **kwargs)

    def get(self, *args, **kwargs):
        # the query.get method does not like it if there is a filter clause
        # pre-loaded, so we need to implement it using a workaround
        obj = self.with_deleted()._get(*args, **kwargs)
        return obj if obj is not None and not obj.deleted_at else None
