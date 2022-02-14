import datetime

from sqlalchemy import or_
from sqlalchemy.dialects.postgresql import UUID, JSONB
from futurewave42.ext import db
from libs.base.model import BaseModel, QueryWithSoftDelete
from libs.error import dynamic_error


class Tag(BaseModel):
    __tablename__ = 'tags'

    name = db.Column(db.String(512), index=True, nullable=False)
    sub_id = db.Column(UUID)
    deleted_at = db.Column(db.DateTime, index=True)

    query_class = QueryWithSoftDelete

    @property
    def children(self):
        if not self.sub_id:
            return self.query.filter(Tag.sub_id == self.id).all()
        return None

    def delete(self):
        self.deleted_at = datetime.datetime.now()
        db.session.commit()

    def update(self, **kwargs):
        sub_id = kwargs.get('sub_id')

        if not self.sub_id and sub_id:
            dynamic_error({}, code=422, message='一级tag不能修改为二级tag')

        if self.sub_id and not sub_id:
            dynamic_error({}, code=422, message='二级tag不能修改为一级tag')

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
        name = kwargs.get('name')
        sub_id = kwargs.get('sub_id', None)
        old_tag = cls.query.filter(cls.name == name).first()

        if old_tag:
            dynamic_error({}, code=422, message='已存在该名称tag')

        tag = cls(
            name=kwargs.get('name'),
        )
        if sub_id:
            tag.sub_id = sub_id

        db.session.add(tag)

        try:
            db.session.commit()
        except Exception as e:
            print(e)
            db.session.rollback()
            dynamic_error({}, code=422, message=str(e))
        return tag

    @classmethod
    def get_tags_by_query(cls, **kwargs):
        page = kwargs.get('page')
        per_page = kwargs.get('per_page')
        q = kwargs.get('q')
        query = cls.query.filter(cls.sub_id.is_(None))

        if q:
            query = query.filter(or_(
                cls.name.ilike("%{}%".format(q)),
            ))

        total = cls.get_count(query)

        if page and per_page:
            query = query.limit(per_page).offset((page - 1) * per_page)
        return query.all(), total
