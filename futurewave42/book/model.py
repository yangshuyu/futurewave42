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


class Book(BaseModel):
    __tablename__ = 'books'

    name = db.Column(db.String(512), index=True, nullable=False)
    author = db.Column(db.String(512))
    language = db.Column(db.String(1024), nullable=False)
    image = db.Column(db.String, nullable=False)
    title = db.Column(db.String, nullable=False)
    images = db.Column(JSONB, default=[])
    context = db.Column(db.String)
    doc = db.Column(db.String)
    docs = db.Column(JSONB, default=[])
    tag_id = db.Column(UUID)
    author_id = db.Column(UUID)

    @property
    def tag(self):
        from futurewave42.tag.model import Tag
        return Tag.query.filter(Tag.id == self.tag_id).first()

    @property
    def new_author(self):
        from futurewave42.author.model import Author
        return Author.query.filter(Author.id == self.author_id).first()

    @property
    def cover(self):
        return '{}{}'.format(load_config().CDN_DOMAIN, self.image)

    @property
    def detail_images(self):
        data = []
        for image in self.images:
            data.append('{}{}'.format(load_config().CDN_DOMAIN, image))
        return data

    def update(self, **kwargs):
        kwargs.pop("tag")
        kwargs.pop("new_author")
        try:
            for k, v in kwargs.items():
                if hasattr(self, k):
                    setattr(self, k, v)

            if kwargs.get('images', None):
                flag_modified(self, 'images')

            if kwargs.get('docs', None):
                flag_modified(self, 'docs')

            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

        return self

    @classmethod
    def add(cls, **kwargs):
        book = cls(
            name=kwargs.get('name'),
            author=kwargs.get('author'),
            language=kwargs.get('language'),
            image=kwargs.get('image'),
            title=kwargs.get('title'),
            images=kwargs.get('images'),
            context=kwargs.get('context'),
            doc=kwargs.get('doc', None),
            docs=kwargs.get('docs', []),
            tag_id=kwargs.get('tag_id', None),
            author_id=kwargs.get('author_id', None)
        )
        db.session.add(book)

        try:
            db.session.commit()
        except Exception as e:
            print(e)
            db.session.rollback()
            dynamic_error({}, code=422, message=str(e))
        return book

    @classmethod
    def get_books_by_query(cls, **kwargs):
        page = kwargs.get('page')
        per_page = kwargs.get('per_page')
        q = kwargs.get('q')
        tag_id = kwargs.get('tag_id')
        author_id = kwargs.get('author_id')

        query = cls.query

        if q:
            query = query.filter(or_(
                cls.name.ilike("%{}%".format(q)),
                cls.title.ilike("%{}%".format(q))

            ))

        if tag_id:
            query = query.filter(cls.tag_id == tag_id)

        if author_id:
            query = query.filter(cls.author_id == author_id)

        total = cls.get_count(query)

        if page and per_page:
            query = query.limit(per_page).offset((page - 1) * per_page)
        return query.all(), total
