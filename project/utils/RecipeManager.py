from random import random

import math
from sqlalchemy import func, and_

from project.database.database import db
from project.database.models import Recipe, RecipeIngredient, Ingredient


class RecipeManager:
    def __init__(self):
        pass

    def isExist(self, recipe_title: str) -> float:
        try:
            recipe = Recipe.query.filter_by(title=recipe_title).first()
            return recipe.recipe_id
        except:
            return -1

    def get_recipe_by_id(self, recipe_id: int) -> Recipe:
        ingredient_relations = RecipeIngredient.query.filter_by(recipe_id=recipe_id).all()
        recipe = {}
        for ingredient_relation in ingredient_relations:
            if 'recipe_id' not in recipe:
                recipe = ingredient_relation.recipe.serialize()
            if 'ingredients' not in recipe:
                recipe['ingredients'] = []
            serialize_ingredient_relation = ingredient_relation.serialize()
            del serialize_ingredient_relation['recipe']
            ingredient = serialize_ingredient_relation['ingredient'].serialize()
            del serialize_ingredient_relation['ingredient']
            ingredient.update(serialize_ingredient_relation)
            recipe['ingredients'].append(ingredient)
        return recipe

    def list_recipe_by_diet(self, diet: str) -> [Recipe]:
        recipe_objects = Recipe.query.filter_by(diet=diet).all()
        recipes = []
        for recipe_object in recipe_objects:
            serialize_recipe = recipe_object.serialize()
            recipes.append(serialize_recipe)
        return recipes

    def save_recipe(self, recipe: dict) -> int:
        recipe_to_save = recipe.copy()
        recipe_to_save['breakfast'] = True
        recipe['recipe_id'] = self.isExist(recipe.get('title'))
        if recipe['recipe_id'] == -1:
            new_recipe = Recipe(**recipe_to_save)
            db.session.add(new_recipe)
            db.session.commit()
            print('ADD RECIPE', new_recipe )
            recipe['recipe_id'] = new_recipe.recipe_id

        return recipe['recipe_id']

    def generate_meal(self, user_diet:str, user_allergies: list) -> list:
        MEAL_PLAN_SIZE = 14
        DAY_PLAN_SIZE = 2

        def _query_recipes(filter_condition):
            return Recipe.query.filter(filter_condition).order_by(func.random()).limit(MEAL_PLAN_SIZE).all()


        def check_week_completion(recipes_list: list,meal_plan_size:int) -> list:
            missing = meal_plan_size - len(recipes_list)
            if missing > 0:
                coeff = DAY_PLAN_SIZE/missing
                for i in range(1, math.ceil(coeff+1)):
                    recipes_list += recipes_list

            return recipes_list[:14]

        safe_ingredients = RecipeIngredient.query.join(Ingredient).filter(
            Ingredient.allergen.notin_(user_allergies)).all()
        recipes_id = {ingredient_relation.recipe_id for ingredient_relation in safe_ingredients}
        filter_condition = Recipe.recipe_id.in_(recipes_id)

        if user_diet.lower() != 'flex':
            filter_condition = and_(Recipe.diet.__eq__(user_diet), filter_condition)

        random_recipes = _query_recipes(filter_condition)

        recipes_list = [recipe.serialize() for recipe in random_recipes]
        recipes_list = check_week_completion(recipes_list, MEAL_PLAN_SIZE)

        # Attach allergens to each recipe
        for recipe in recipes_list:
            recipe_id = recipe['recipe_id']
            recipe['allergens'] = set()

            for ingredient_relation in safe_ingredients:
                if ingredient_relation.recipe.recipe_id == recipe_id and ingredient_relation.ingredient.allergen is not None:
                    recipe['allergens'].add(ingredient_relation.ingredient.allergen.lower())

        # Plan meals for each day
        meal_plan = []
        day_plan = []

        for recipe in recipes_list:
            recipe['allergens'] = list(recipe.get('allergens', set()))
            day_plan.append(recipe)

            if len(day_plan) == DAY_PLAN_SIZE:
                meal_plan.append(day_plan)
                day_plan = []

        return meal_plan
