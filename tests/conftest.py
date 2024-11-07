import json
import os, pytest


from dotenv import load_dotenv
from sqlalchemy import func

from project.app import app
from project.database.models import User

load_dotenv()

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

@pytest.fixture
def user():
    with app.app_context():
        user = User.query.order_by(func.random()).limit(1).all()
        return user[0]

@pytest.fixture
def user_good_password():
    return 'kebab'

@pytest.fixture
def user_bad_password():
    return 'waffle'

@pytest.fixture
def user_diet(user):
    return user.dietaryPreference

@pytest.fixture
def user_allergies(user):
    return user.allergies

@pytest.fixture
def authentication_header(client, user, user_good_password):
    response = client.post('/user/login', json={'email': user.email, 'password': user_good_password})
    data = json.loads(response.data)
    token = data['jwtoken']
    return {"authorization": f"Bearer {token}"}
