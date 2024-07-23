from datetime import datetime, timezone, timedelta

import jwt

from project.database.database import db
from project.database.models import User


class UserManager:
    def __init__(self, app):
        self.SECRET_KEY = app.config['SECRET_KEY']
        pass

    def isExist(self, email: str) -> float:
        try:
            user = User.query.filter_by(email=email).first()
            return user.user_id
        except:
            return -1

    def login(self, user: dict):
        user_db = User.query.filter_by(email=user.get('email', '')).first()
        if user_db is None:
            return False, {}

        is_logged = user_db.check_password(user.get('password', ''))
        if is_logged:
            user_to_send = user_db.serialize()
            user_to_send.update({'jwtoken': self.generate_token(user_db.user_id)})
            return True, user_to_send
        else:
            return False, {}

    def add_user(self, user: dict):
        user_to_save = user.copy()
        del user_to_save['password']
        user['user_id'] = self.isExist(user_to_save.get('email'))
        if user['user_id'] == -1:
            new_user = User(**user_to_save)
            new_user.set_password(user['password'])
            db.session.add(new_user)
            db.session.commit()
            print('ADD USER', new_user)
            return new_user.serialize()
        else :
            return 409

    def generate_token(self, user_id: int) -> str:
        payload = {
            'user_id': user_id,
            'exp': datetime.now(timezone.utc) + timedelta(days=1)
        }
        return jwt.encode(payload, self.SECRET_KEY, algorithm='HS256')

    @staticmethod
    def decode_token(self, token):
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=['HS256'])
            return payload['sub']
        except jwt.ExpiredSignatureError:
            return 'Token expired. Please log in again.'
        except jwt.InvalidTokenError:
            return 'Invalid token. Please log in again.'