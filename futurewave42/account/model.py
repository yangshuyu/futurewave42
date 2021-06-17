from sqlalchemy.dialects.postgresql import UUID
from werkzeug.security import generate_password_hash, check_password_hash

# from libs.base.model import BaseModel
from futurewave42.ext import db
from libs.base.model import BaseModel
from libs.redis import redis_client


class User(BaseModel):
    __tablename__ = 'users'

    name = db.Column(db.String(255), index=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(255), index=True, unique=True)
    password_hash = db.Column(db.String(256))
    active = db.Column(db.Boolean(), default=True)
    avatar_url = db.Column(db.String(512), default='imgs/C9372FE1-C7DA-4612-BF36-134F4AD271E0.jpg')

    __table_args__ = (
        db.UniqueConstraint(
            'email',
            name='email_uc'),
    )

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    @classmethod
    def get_user_by_email(cls, **kwargs):
        email = kwargs.get('email')
        u = cls.query.filter(cls.email == email).first()
        return u


class Role(BaseModel):
    __tablename__ = 'roles'
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


class UserRole(BaseModel):
    __tablename__ = 'users_roles'

    user_id = db.Column(UUID, index=True)
    role_id = db.Column(UUID, index=True)
