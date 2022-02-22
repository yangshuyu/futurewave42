from sqlalchemy import or_
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

    tag_id = db.Column(UUID)
    author_id = db.Column(UUID)
    tag_ids = db.Column(JSONB, default=[])
    author_ids = db.Column(JSONB, default=[])
    origin_tags = db.Column(JSONB, default=[])

    @property
    def tags(self):
        from futurewave42.tag.model import Tag
        if not self.tag_ids:
            return []
        return db.session.query(Tag).filter(Tag.id.in_(self.tag_ids)).all()

    @property
    def new_authors(self):
        from futurewave42.author.model import Author
        if not self.author_ids:
            return []
        return db.session.query(Author).filter(Author.id.in_(self.author_ids)).all()

    @property
    def cover(self):
        return '{}{}'.format(load_config().CDN_DOMAIN, self.image)

    def update(self, **kwargs):
        kwargs.pop("tags", None)
        kwargs.pop("tag", None)
        kwargs.pop("new_author", None)
        kwargs.pop("new_authors", None)

        try:
            for k, v in kwargs.items():
                if hasattr(self, k):
                    setattr(self, k, v)

            if kwargs.get('tag_ids', None):
                flag_modified(self, 'tag_ids')

            if kwargs.get('author_ids', None):
                flag_modified(self, 'author_ids')

            if kwargs.get('origin_tags', None):
                flag_modified(self, 'origin_tags')

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
            tag_ids=kwargs.get('tag_ids', []),
            author_ids=kwargs.get('author_ids', []),
            origin_tags=kwargs.get('origin_tags', [])
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
        q = kwargs.get('q')
        tag_id = kwargs.get('tag_id')
        author_id = kwargs.get('author_id')

        if q:
            query = query.filter(or_(
                cls.name.ilike("%{}%".format(q)),
                cls.title.ilike("%{}%".format(q))

            ))

        if tag_id:
            query = query.filter(cls.tag_ids.cast(JSONB).op("@>")([tag_id]))

        if author_id:
            query = query.filter(cls.author_id.cast(JSONB).op("@>")([author_id]))
        query = query.order_by(cls.created_at.desc())
        total = cls.get_count(query)

        if page and per_page:
            query = query.limit(per_page).offset((page - 1) * per_page)
        return query.all(), total
