from flask import Blueprint
from flask import request, Response
import json
from openai import OpenAI
from project.utils.IngredientManager import IngredientManager
from project.utils.RecipeManager import RecipeManager
from project.utils.UserManager import UserManager


route_blueprint = Blueprint('route', __name__,)

@route_blueprint.route('/')
def hello_world():  # put application's code here
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

@route_blueprint.route('/dev/recipe/generate', methods=['GET'])
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


@route_blueprint.route('/recipe/diet', methods=['GET'])
def handle_get_recipes_by_diet():
    diet = request.args.get('filter')
    print(diet)
    recipe_mgt = RecipeManager()
    recipes = recipe_mgt.list_recipe_by_diet(diet)
    return recipes

    # list_recipe_by_diet
@route_blueprint.route('/recipe/id/<recipe_id>', methods=['GET'])
def handle_get_recipe(recipe_id: int):
    recipe_mgt = RecipeManager()
    recipe = recipe_mgt.get_recipe_by_id(recipe_id)
    print(recipe)
    return recipe

@route_blueprint.route('/user', methods=['POST'])
def handle_add_user():
    user_data = request.get_json()
    user_mgt = UserManager()
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

@route_blueprint.errorhandler(404)
def page_not_found(e):
    print('404')
    return f'{request.path} - Not found'
