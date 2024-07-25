from datetime import date, timedelta, datetime
import random

import math
from sqlalchemy import func, and_

from project.database.database import db
from project.database.models import Recipe, RecipeIngredient, Ingredient, MealPlans, MealPlanRecipe, User


class RecipeManager:
    def __init__(self):
        self.today = date.today()
        self.current_week_date = self.today - timedelta(days=self.today.weekday())
        self.next_week_date = self.today + timedelta(days=(7 - self.today.weekday()))

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


    def swap_recipe(self, current_recipe_id: int, date_to_act:str, current_user: User) -> list:
        """
        :param current_recipe_id: The ID of the current recipe to be swapped.
        :param date_to_act: The date on which the swap should be made.
        :param current_user: The user for whom the recipe swap is being done.
        :return: The updated current meal plan for the user.

        This method swaps the current recipe with a randomly selected recipe from the meal plan for a specific date and user.

        """
        safe_ingredients = RecipeIngredient.query.join(Ingredient).filter(
            Ingredient.allergen.notin_(current_user.allergies)).all()
        recipes_id = {ingredient_relation.recipe_id for ingredient_relation in safe_ingredients}
        recipes_id.remove(current_recipe_id)

        new_recipe_id = random.choice(list(recipes_id))

        meal_plan = MealPlans.query.filter(
            and_(
                MealPlans.start_date == self.current_week_date,
                MealPlans.user_id == current_user.user_id )
        ).first()

        meal_plan_recipe_relation = MealPlanRecipe.query.filter(
            and_(
                MealPlanRecipe.meal_plan_id == meal_plan.meal_plan_id,
                MealPlanRecipe.recipe_id == current_recipe_id,
                MealPlanRecipe.date == datetime.strptime(date_to_act, "%Y-%m-%d")
            )).first()

        meal_plan_recipe_relation.recipe_id = new_recipe_id
        db.session.commit()

        return self.get_current_meal_plan(current_user)

    def format_meal_plan(self,recipe_list, start_date, current_user):

        def get_date_of_meal(day_idx):
            day_date = start_date + timedelta(days=(day_idx))
            return day_date.strftime("%Y-%m-%d")

        MEAL_PLAN_SIZE = 14
        DAY_PLAN_SIZE = 2

        meal_plan = []
        day_plan = []

        safe_ingredients = RecipeIngredient.query.join(Ingredient).filter(
            Ingredient.allergen.notin_(current_user.allergies)).all()

        day_idx = 0
        for recipe in recipe_list:

            recipe_id = recipe['recipe_id']

            recipe['allergens'] = set()

            for ingredient_relation in safe_ingredients:
                if ingredient_relation.recipe.recipe_id == recipe_id and ingredient_relation.ingredient.allergen is not None:
                    recipe['allergens'].add(ingredient_relation.ingredient.allergen.lower())

            recipe['allergens'] = list(recipe.get('allergens', set()))
            recipe['date'] = get_date_of_meal(day_idx)
            day_plan.append(recipe)
            if len(day_plan) == DAY_PLAN_SIZE:
                day_idx += 1
                meal_plan.append(day_plan)
                day_plan = []

        return meal_plan

    def get_current_meal_plan(self, current_user):
        current_meal_plan = MealPlans.query.filter(and_(MealPlans.start_date == self.current_week_date,MealPlans.user_id == current_user.user_id )).first()
        meal_plan_recipe_relations = MealPlanRecipe.query.filter(
            MealPlanRecipe.meal_plan_id == current_meal_plan.meal_plan_id).order_by(MealPlanRecipe.date,MealPlanRecipe.meal_plans_recipe_relation_id).all()

        recipe_list = [meal_plan_recipe_relation.recipe.serialize() for meal_plan_recipe_relation in meal_plan_recipe_relations]

        return self.format_meal_plan(recipe_list, current_meal_plan.start_date, current_user)

    def generate_meal(self, current_user) -> list:
        MEAL_PLAN_SIZE = 14
        DAY_PLAN_SIZE = 2

        def delete_meal_plan_recipes(meal_plan_id: int):
            MealPlanRecipe.query.filter(MealPlanRecipe.meal_plan_id == meal_plan_id).delete()
            db.session.commit()

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
            Ingredient.allergen.notin_(current_user.allergies)).all()
        recipes_id = {ingredient_relation.recipe_id for ingredient_relation in safe_ingredients}
        filter_condition = Recipe.recipe_id.in_(recipes_id)

        if current_user.dietaryPreference.lower() != 'flex':
            filter_condition = and_(Recipe.diet.__eq__(current_user.dietaryPreference), filter_condition)

        random_recipes = _query_recipes(filter_condition)

        recipe_list = [recipe.serialize() for recipe in random_recipes]
        recipe_list_completed = check_week_completion(recipe_list, MEAL_PLAN_SIZE)


        today = date.today()
        if today.weekday() < 5:
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
        else:
            start_date = today + timedelta(days=(7 - today.weekday()))
            end_date = start_date + timedelta(days=6)

        meal_plan_to_save = {
            'user_id': current_user.user_id,
            'start_date': start_date,
            'end_date': end_date
        }

        meal_plan = self.format_meal_plan(recipe_list_completed,start_date, current_user)

        meal_plan_obj = MealPlans.query.filter(and_(MealPlans.user_id == current_user.user_id, MealPlans.start_date == start_date)).first()

        if meal_plan_obj:
            meal_plan_obj.user_id = current_user.user_id
            meal_plan_obj.start_date = start_date
            meal_plan_obj.end_date = end_date
        else:
            meal_plan_obj = MealPlans(**meal_plan_to_save)
            db.session.add(meal_plan_obj)

        db.session.commit()

        delete_meal_plan_recipes(meal_plan_obj.meal_plan_id)
        for day_idx, day in enumerate(meal_plan):
            day_date = start_date + timedelta(days=(day_idx))

            for meal_idx, meal in enumerate(day):
                meal_plan_recipe = MealPlanRecipe(
                        meal_plan_id=meal_plan_obj.meal_plan_id,
                        recipe_id=meal['recipe_id'],
                        mealType='lunch' if meal_idx == 0 else 'dinner',
                        date=day_date
                    )
                db.session.add(meal_plan_recipe)
                db.session.commit()

        return meal_plan
