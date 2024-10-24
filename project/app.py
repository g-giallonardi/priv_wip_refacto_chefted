import json
import os

from flask import request, Response
from dotenv import load_dotenv
from flask_cors import CORS

from project.database.models import User
from project import create_app
from openai import OpenAI

from project.utils.IngredientManager import IngredientManager
from project.utils.RecipeManager import RecipeManager
from project.utils.UserManager import UserManager
from project.utils.decorator import token_required, log_endpoint_access, pay_action_cost

load_dotenv()

app = create_app(os.getenv('SQLALCHEMY_DATABASE_URI', None))
CORS(app)
@app.route('/')
def hello_world():
    return Response(
        "Method not allowed", status=405, mimetype='text/plain'
    )

def generate_recipe(recipe_name: str, diet_type: str):
    prompt = ''
    with open('resources/prompts/recipeGenerationJson.prompt', 'r') as file:
        prompt = file.read()
    prompt = prompt.replace('{recipe_name}', recipe_name).replace('{diet_type}', diet_type)

    client = OpenAI()
    completion = client.chat.completions.create(
      model="gpt-4o",
      response_format={"type": "json_object"},
      messages=[
        {"role": "system", "content": 'tu es un assistant culinaire.'},
        {"role": "user", "content": prompt}
      ]
    )
    return completion.choices[0].message.content

@app.route('/dev/recipe/generate', methods=['GET'])
def handle_generate_recipe():
    recipe_mgt = RecipeManager()
    ingredient_mgt = IngredientManager()
    recipes = set()
    ideas = []
    with open('resources/prompts/mealIdeas', 'r') as file:
        ideas = json.loads(file.read())


    for idea in ideas:
        recipe_name = idea.get('name')
        diet_type = idea.get('type')

        recipe = json.loads(generate_recipe(recipe_name, diet_type))
        recipe_ingredients = recipe.pop('ingredients', None)

        if recipe_mgt.isExist(recipe.get('title')) == -1 :
            recipe_id = recipe_mgt.save_recipe(recipe)
            recipes.add((recipe.get('title'), recipe_id))
            for ingredient in recipe_ingredients:
                ingredient_mgt.save_ingredient(recipe_id, ingredient)

    return list(recipes)

@app.route('/user/me', methods=['GET'])
@token_required
def handle_get_current_user(current_user: User):

    userMgt = UserManager(app)
    user = userMgt.get_current_user(current_user.user_id).serialize()

    return Response(
        json.dumps(user), status=200, mimetype='application/json'
    )

@app.route('/recipe/diet', methods=['GET'])
@token_required
def handle_get_recipes_by_diet():
    diet = request.args.get('filter')
    recipe_mgt = RecipeManager()
    recipes = recipe_mgt.list_recipe_by_diet(diet)
    return recipes

    # list_recipe_by_diet
@app.route('/recipe/id/<recipe_id>', methods=['GET'])
@token_required
@log_endpoint_access
def handle_get_recipe(current_user: User, args: dict) -> Response:
    """
    Handle the GET request for retrieving a recipe.

    :param current_user: The current user making the request.
    :param args: The arguments passed in the request URL.
    :return: The response containing the retrieved recipe in JSON format.
    """
    recipe_mgt = RecipeManager()
    recipe = recipe_mgt.get_recipe_by_id(args['recipe_id'])
    return Response(
        json.dumps(recipe), status=200, mimetype='application/json'
    )

@app.route('/user/login', methods=['POST'])
def handle_user_login() -> Response:
    """
    Handles user login process.

    :return: Returns a Response object.
    :rtype: flask.Response
    """
    user_data = request.get_json()
    user_mgt = UserManager(app)
    is_logged, user = user_mgt.login(user_data)
    if is_logged:
        return Response(
            json.dumps(user), status=200, mimetype='application/json'
        )
    else:
        return Response(
            "Bad credentials", status=401, mimetype='application/json'
        )

@app.route('/user', methods=['POST'])
def handle_add_user() -> Response:
    """
    Handle Add User

    This method is used to handle the POST request for adding a new user.

    :return: The response object containing relevant information.
    """
    user_data = request.get_json()
    user_mgt = UserManager(app)
    user = user_mgt.add_user(user_data)
    print(user)
    if user == 409:
        return Response(
            "Email already registered", status=409
        )
    else:
        return Response(
            json.dumps(user), status=201,mimetype='application/json'
        )

@app.route('/meal/generate', methods=['POST'])
@token_required
@log_endpoint_access
@pay_action_cost(cost=0)
def handle_generate_meal(current_user: User, args: dict) -> Response:
    """
    :param current_user: The current user, of type User, who is requesting to generate a meal.
    :param args: Additional arguments for the endpoint.
    :return: The generated meal as a Response object.

    This method is the endpoint for generating a meal. It requires the current user object and any additional arguments passed to the endpoint. It returns the generated meal as a Response
    * object.

    Example usage:

        current_user = User(...)
        args = {...}
        response = handle_generate_meal(current_user, args)

    """
    start_date = args['start_date']
    generated_meal = []
    recipe_mgt = RecipeManager()
    recipes = recipe_mgt.generate_meal(current_user, start_date)

    for recipe in recipes:
        generated_meal.append(recipe)
    return Response(
        json.dumps(generated_meal), status=200, mimetype='application/json'
    )

@app.route('/meal/plan', methods=['POST'])
@token_required
@log_endpoint_access
def handle_get_current_meal_plan(current_user: User, args: dict) -> Response:
    recipe_mgt = RecipeManager()
    user_mgt = UserManager(app)
    current_user = user_mgt.get_current_user(current_user.user_id)
    current_meal_plan = recipe_mgt.get_current_meal_plan(current_user,args)

    data_to_send = current_meal_plan
    if data_to_send is None:
        data_to_send = []
    return Response(
        json.dumps(data_to_send), status=200, mimetype='application/json'
    )
@app.route('/meal/swap', methods=['POST'])
@token_required
@log_endpoint_access
@pay_action_cost(cost=0)
def handle_swap_recipe_in_meal(current_user: User, args: dict) -> Response:
    recipe_id_to_swap = args['recipe_id']
    date_to_act = args['date']

    recipe_mgt = RecipeManager()
    user_mgt = UserManager(app)

    current_user = user_mgt.get_current_user(current_user.user_id)

    recipe_mgt.swap_recipe(recipe_id_to_swap, date_to_act, current_user)
    new_recipe = recipe_mgt._get_recipe_by_date(current_user, date_to_act)

    if new_recipe:
        return Response(
            json.dumps(new_recipe), status=200, mimetype='application/json'
        )
    else:
        return Response(
            "Recipe not found", status=404, mimetype='application/json'
        )

@app.errorhandler(404)
def page_not_found(e:Exception) -> Response:
    """
    :param e: The exception object that caused the 404 error.
    :return: A Response object with the error message and status code 404.
    """
    return Response(
        f'{request.path} - Not found', status=404
    )


if __name__ == '__main__':

    app.run()
