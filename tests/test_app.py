import json
from datetime import datetime, timedelta

import pytest
from sqlalchemy import desc

from project.database.models import Log


def test_no_route_endpoint(client):
    response = client.get('/')
    assert response.status_code == 405
    assert response.data == b"Method not allowed"

def test_generate_log(client,user, authentication_header):
    endpoint = '/meal/generate'
    response = client.get(endpoint, headers=authentication_header)
    user_id = user.user_id
    log = Log.query.filter_by(user_id=user_id).order_by(desc(Log.timestamp)).first()
    now = datetime.now().replace(tzinfo=None)
    difference = now - (log.timestamp.replace(tzinfo=None)+ timedelta(hours=2))
    assert response.status_code == 200
    assert log.user_id == user_id
    assert log.url == f'http://localhost{endpoint}'
    assert difference.total_seconds() < 5


def check_generate_meal_structure(meal_plan):
    assert isinstance(meal_plan, list) is True
    assert len(meal_plan) == 7
    assert isinstance(meal_plan[0], list) is True
    assert len(meal_plan[0]) == 2


def check_generate_meal_diet(meal_plan, user_diet):
    for day_plan in meal_plan:
        assert day_plan[0].get('diet') == user_diet
        assert day_plan[1].get('diet') == user_diet


def check_generate_meal_allergens(meal_plan, user_allergies):
    allergies = {allergy.lower() for allergy in user_allergies}
    allergens = set()
    for day_plan in meal_plan:
        assert isinstance(day_plan[0].get('allergens'), list)
        assert isinstance(day_plan[1].get('allergens'), list)
        allergens.update(day_plan[0].get('allergens'))
        allergens.update(day_plan[1].get('allergens'))
    assert len(allergens.intersection(allergies)) == 0


@pytest.mark.skip()
def test_generate_meal(client, user_diet,user_allergies):
    response = client.get('/meal/generate')
    assert response.status_code == 200
    meal_plan = json.loads(response.data)

    check_generate_meal_structure(meal_plan)
    if user_diet.lower() != 'flex':
        check_generate_meal_diet(meal_plan, user_diet)
    check_generate_meal_allergens(meal_plan, user_allergies)

def test_login_user(client,user,user_good_password, user_bad_password):
    #Test with bad credentials => 401
    response = client.post('/user/login', json={'email': user.email, 'password': user_bad_password})
    assert response.status_code == 401

    #Test with good credentials => 200
    response = client.post('/user/login', json={'email': user.email, 'password': user_good_password})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, dict)
    assert 'email' in data
    assert 'jwtoken' in data
    assert data['email'] == user.email
