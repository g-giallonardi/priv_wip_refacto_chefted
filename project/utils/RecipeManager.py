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

    def _start_of_week(self, date_to_act: str):
        date_to_act = datetime.strptime(date_to_act, "%Y-%m-%d")
        result = date_to_act - timedelta(days=date_to_act.weekday())
        return result

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
            recipe['recipe_id'] = new_recipe.recipe_id

        return recipe['recipe_id']

    def swap_recipe(self, current_recipe_id: int, date_to_act: str, current_user: User) -> list:
        """
        :param current_recipe_id: The ID of the current recipe to be swapped.
        :param date_to_act: The date on which the swap should be made.
        :param current_user: The user for whom the recipe swap is being done.
        :return: The updated current meal plan for the user.

        This method swaps the current recipe with a randomly selected recipe from the meal plan for a specific date and user.

        """
        safe_recipe_ingredients = RecipeIngredient.query.join(Ingredient).filter(
            Ingredient.allergen.notin_(current_user.allergies)).all()

        safe_recipes_ids = {ingredient_relation.recipe_id for ingredient_relation in safe_recipe_ingredients}
        safe_recipes_ids.remove(current_recipe_id)

        new_recipe_id = random.choice(list(safe_recipes_ids))

        current_meal_plan = MealPlans.query.filter(
            and_(
                MealPlans.start_date == self._start_of_week(date_to_act),
                MealPlans.user_id == current_user.user_id)
        ).first()

        meal_plan_recipe_relation_to_swap = MealPlanRecipe.query.filter(
            and_(
                MealPlanRecipe.meal_plan_id == current_meal_plan.meal_plan_id,
                MealPlanRecipe.recipe_id == current_recipe_id,
                MealPlanRecipe.date == datetime.strptime(date_to_act, "%Y-%m-%d")
            )).first()

        meal_plan_recipe_relation_to_swap.recipe_id = new_recipe_id

        db.session.commit()

        return self.get_current_meal_plan(current_user, {"start": self._start_of_week(date_to_act)})

    def _extract_allergen(self, ingredient) -> str:

        allergen = ingredient.allergen
        if allergen:
            return allergen

        return None

    def _get_recipe_allergen(self, recipe_id) -> set:
        allergens = set()

        raw_recipe_ingredients = (RecipeIngredient.query
                                  .join(Ingredient)
                                  .filter(
                                    RecipeIngredient.recipe_id == recipe_id).all())

        for raw_recipe_ingredient in raw_recipe_ingredients:
            allergen = self._extract_allergen(raw_recipe_ingredient.ingredient)
            if allergen:
                allergens.add(allergen)

        return allergens

    def format_meal_plan(self, recipe_list, start_date):

        def get_date_of_meal(day_idx):
            day_date = start_date + timedelta(days=day_idx)
            return day_date.strftime("%Y-%m-%d")

        DAY_PLAN_SIZE: int = 2

        meal_plan: list[list] = []
        day_plan: list = []

        day_idx: int = 0

        for recipe in recipe_list:

            recipe_id = recipe['recipe_id']

            recipe['allergens'] = list(self._get_recipe_allergen(recipe_id))
            recipe['date'] = get_date_of_meal(day_idx)

            day_plan.append(recipe)

            if len(day_plan) == DAY_PLAN_SIZE:
                day_idx += 1
                meal_plan.append(day_plan)
                day_plan = []

        return meal_plan

    def get_current_meal_plan(self, current_user: User, date=None) -> None | list:
        start_date = date['start'] if date else self.current_week_date
        current_meal_plan = MealPlans.query.filter(
            and_(MealPlans.start_date == start_date, MealPlans.user_id == current_user.user_id)).first()

        if current_meal_plan is None:
            return None

        meal_plan_recipe_relations = MealPlanRecipe.query.filter(
            MealPlanRecipe.meal_plan_id == current_meal_plan.meal_plan_id).order_by(MealPlanRecipe.date,
                                                                                    MealPlanRecipe.meal_plans_recipe_relation_id).all()

        recipe_list = [meal_plan_recipe_relation.recipe.serialize() for meal_plan_recipe_relation in
                       meal_plan_recipe_relations]

        return self.format_meal_plan(recipe_list, current_meal_plan.start_date)

    def generate_meal(self, current_user: User, start_date: str) -> list:
        MEAL_PLAN_SIZE = 14
        DAY_PLAN_SIZE = 2

        def delete_meal_plan_recipes(meal_plan_id: int):
            MealPlanRecipe.query.filter(MealPlanRecipe.meal_plan_id == meal_plan_id).delete()
            db.session.commit()

        def query_recipes(filter_condition):
            return Recipe.query.filter(filter_condition).order_by(func.random()).limit(MEAL_PLAN_SIZE).all()

        def check_week_completion(recipes_list: list, meal_plan_size: int) -> list:
            missing = meal_plan_size - len(recipes_list)
            if missing > 0:
                coeff = DAY_PLAN_SIZE / missing
                for i in range(1, math.ceil(coeff + 1)):
                    recipes_list += recipes_list

            return recipes_list[:14]

        safe_ingredients = RecipeIngredient.query.join(Ingredient).filter(
            Ingredient.allergen.notin_(current_user.allergies)).all()
        recipes_id = {ingredient_relation.recipe_id for ingredient_relation in safe_ingredients}
        filter_condition = Recipe.recipe_id.in_(recipes_id)

        if current_user.dietaryPreference.lower() != 'flex':
            filter_condition = and_(Recipe.diet.__eq__(current_user.dietaryPreference), filter_condition)

        random_recipes = query_recipes(filter_condition)

        recipe_list = [recipe.serialize() for recipe in random_recipes]
        recipe_list_completed = check_week_completion(recipe_list, MEAL_PLAN_SIZE)

        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = start_date + timedelta(days=6)

        meal_plan_to_save = {
            'user_id': current_user.user_id,
            'start_date': start_date,
            'end_date': end_date
        }

        meal_plan = self.format_meal_plan(recipe_list_completed, start_date)

        meal_plan_obj = MealPlans.query.filter(
            and_(MealPlans.user_id == current_user.user_id, MealPlans.start_date == start_date)).first()

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
            day_date = start_date + timedelta(days=day_idx)

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
