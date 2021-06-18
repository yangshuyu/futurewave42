from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm.attributes import flag_modified
from werkzeug.security import generate_password_hash, check_password_hash

# from libs.base.model import BaseModel
from config import load_config
from futurewave42.ext import db
from libs.base.model import BaseModel
from libs.error import dynamic_error
from libs.redis import redis_client


class Video(BaseModel):
    __tablename__ = 'videos'

    name = db.Column(db.String(512))
    image = db.Column(db.String, nullable=False)
    title = db.Column(db.String, nullable=False)
    video = db.Column(db.String, nullable=False)
    context = db.Column(db.String)
    doc = db.Column(db.String)

    @property
    def cover(self):
        return '{}{}'.format(load_config().CDN_DOMAIN, self.image)

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
        video = cls(
            name=kwargs.get('name'),
            image=kwargs.get('image'),
            title=kwargs.get('title'),
            video=kwargs.get('video'),
            context=kwargs.get('context'),
            doc=kwargs.get('doc', None),
        )
        db.session.add(video)

        try:
            db.session.commit()
        except Exception as e:
            print(e)
            db.session.rollback()
            dynamic_error({}, code=422, message=str(e))
        return video

    @classmethod
    def get_videos_by_query(cls, **kwargs):
        page = kwargs.get('page')
        per_page = kwargs.get('per_page')
        query = cls.query

        total = cls.get_count(query)

        if page and per_page:
            query = query.limit(per_page).offset((page - 1) * per_page)
        return query.all(), total
