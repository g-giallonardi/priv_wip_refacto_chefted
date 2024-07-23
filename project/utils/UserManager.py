from datetime import datetime, timezone, timedelta

import jwt

from project.database.database import db
from project.database.models import User


class UserManager:
    """
    Class UserManager

    The UserManager class provides functionality for managing user data and authentication.

    Attributes:
        SECRET_KEY (str): The secret key used for generating JWT tokens.

    Methods:
        __init__(self, app)
            Initializes a new instance of the UserManager class.

            Parameters:
                app (object): The application object containing configuration.

        isExist(self, email: str) -> float
            Checks if a user with the specified email exists in the database.

            Parameters:
                email (str): The email address of the user to check.

            Returns:
                float: The user ID if the user exists, -1 otherwise.

        login(self, user: dict)
            Authenticates a user based on the provided credentials.

            Parameters:
                user (dict): A dictionary containing the user's email and password.

            Returns:
                tuple: A tuple containing a boolean indicating if the user was successfully authenticated and a dictionary
                       containing the authenticated user's data and JWT token if authentication was successful, otherwise an
                       empty dictionary.

        add_user(self, user: dict)
            Adds a new user to the database.

            Parameters:
                user (dict): A dictionary containing the user's data including email, password, and other optional fields.

            Returns:
                object/int: If the user is successfully added, it returns a serialized representation of the added user.
                            If a user with the same email already exists, it returns the HTTP status code 409 indicating a
                            conflict.

        generate_token(self, user_id: int) -> str
            Generates a JWT token for the specified user ID.

            Parameters:
                user_id (int): The ID of the user.

            Returns:
                str: The generated JWT token.

        decode_token(self, token)
            Decodes the provided JWT token and retrieves the user ID.

            Parameters:
                token (str): The JWT token to decode.

            Returns:
                str: The decoded user ID if the token is valid, otherwise an error message indicating the reason for the
                     invalid token.
    """
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
        user_to_save['tokenCount'] = 10
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