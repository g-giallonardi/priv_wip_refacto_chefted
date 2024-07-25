import json
from datetime import datetime, timedelta
import random

import pytest
from sqlalchemy import desc

from project.database.database import db
from project.database.models import Log, User, MealPlans, MealPlanRecipe


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


def test_generate_meal(client, authentication_header, user, user_diet, user_allergies):
    TEST_ACTION_TOKEN_COUNT = 10
    current_token_count = user.tokenCount
    assign_token(user, TEST_ACTION_TOKEN_COUNT)

    # Test endpoint
    response = client.get('/meal/generate', headers=authentication_header)
    assert response.status_code == 200
    meal_plan_api = json.loads(response.data)
    check_generate_meal_structure(meal_plan_api)
    if user_diet.lower() != 'flex':
        check_generate_meal_diet(meal_plan_api, user_diet)
    check_generate_meal_allergens(meal_plan_api, user_allergies)

    # Test DB consistence
    meal_plan_db = MealPlans.query.filter_by(user_id=user.user_id).order_by(desc(MealPlans.meal_plan_id)).first()
    meal_plan_db.user_id = user.user_id
    meal_plan_id = meal_plan_db.meal_plan_id

    meal_plan_relations = MealPlanRecipe.query.filter_by(meal_plan_id=meal_plan_id).all()
    assert isinstance(meal_plan_relations, list)
    assert len(meal_plan_relations) == 14

    db_recipe_id = {meal_plan_relation.recipe_id for meal_plan_relation in meal_plan_relations}

    api_recipe_id = set()
    for day in meal_plan_api:
        for meal in day:
            api_recipe_id.add(meal['recipe_id'])

    assert api_recipe_id == db_recipe_id

    assign_token(user, current_token_count)


def test_login_user(client,user,user_good_password):
    response = client.post('/user/login', json={'email': user.email, 'password': user_good_password})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, dict)
    assert 'email' in data
    assert 'jwtoken' in data
    assert data['email'] == user.email


def test_bad_login_user(client,user, user_bad_password):
    response = client.post('/user/login', json={'email': user.email, 'password': user_bad_password})
    assert response.status_code == 401


def assign_token(user,token_count):
    user_db = User.query.get(user.user_id)
    user_db.tokenCount = token_count
    db.session.commit()


def test_use_action_token(client,authentication_header, user):
    TEST_ACTION_TOKEN_COUNT = 10
    current_token_count = user.tokenCount

    #Test action decrement
    assign_token(user, TEST_ACTION_TOKEN_COUNT)
    response = client.get('/meal/generate', headers=authentication_header)
    assert response.status_code == 200
    user_db = User.query.get(user.user_id)
    assert user_db.tokenCount < TEST_ACTION_TOKEN_COUNT

    #reset count
    assign_token(user, current_token_count)


def test_no_more_action_token(client,authentication_header, user):
    current_token_count = user.tokenCount

    assign_token(user, 0)
    response = client.get('/meal/generate', headers=authentication_header)
    assert response.status_code == 403

    # reset count
    assign_token(user, current_token_count)


def test_get_specific_recipe(client, user, authentication_header):
    current_token_count = user.tokenCount
    assign_token(user, 10)

    #get meal plan to get a recipe_id
    response = client.get('/meal/generate', headers=authentication_header)
    assert response.status_code == 200
    meal_plan = json.loads(response.data)
    recipe_id_wanted = meal_plan[0][0]['recipe_id']

    # Get recipe from the recipe_id found and apply test
    response = client.get(f'/recipe/id/{recipe_id_wanted}', headers=authentication_header)
    assert response.status_code == 200
    recipe = json.loads(response.data)
    assert isinstance(recipe,dict)
    assert 'recipe_id' in recipe
    assert recipe_id_wanted == recipe['recipe_id']

    # reset count
    assign_token(user, current_token_count)


@pytest.mark.dev
def test_swap_recipe_in_meal_plan(client, user, authentication_header):
    current_token_count = user.tokenCount
    assign_token(user, 10)

    # get meal plan to get a recipe_id
    response = client.get('/meal/plan', headers=authentication_header)
    assert response.status_code == 200
    meal_plan = json.loads(response.data)
    current_recipe_ids = []
    for day in meal_plan:
        for meal in day:
            current_recipe_ids.append(meal['recipe_id'])

    recipe_idx = random.randrange(len(current_recipe_ids))

    recipe_id_to_swap = meal_plan[3][1]['recipe_id']
    date_to_act = meal_plan[3][1]['date']

    response = client.post('/meal/swap', headers=authentication_header, json={'recipe_id': recipe_id_to_swap, 'date':date_to_act})
    assert response.status_code == 200

    new_meal_plan_api = json.loads(response.data)
    assert isinstance(new_meal_plan_api, list)

    check_generate_meal_structure(new_meal_plan_api)
    new_recipe_ids = [meal['recipe_id'] for day in new_meal_plan_api for meal in day]

    assert recipe_id_to_swap not in new_recipe_ids

    # reset count
    assign_token(user, current_token_count)
