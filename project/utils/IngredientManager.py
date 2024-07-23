from project.database.database import db
from project.database.models import Ingredient, RecipeIngredient

class IngredientManager:
    def __init__(self):
        pass

    def isExist(self, ingredient: str) -> float:
        try:
            ingredient = Ingredient.query.filter_by(name=ingredient).first()
            return ingredient.ingredient_id
        except:
            return -1

    def save_ingredient(self, recipe_id: int, ingredient: dict) -> bool:
        ingredient['ingredient_id'] = self.isExist(ingredient.get('name'))
        if ingredient['ingredient_id'] == -1:
            new_ingredient = Ingredient(name=ingredient.get('name'), category=ingredient.get('category'))
            db.session.add(new_ingredient)
            db.session.commit()
            print('ADD INGREDIENT', new_ingredient)
            ingredient['ingredient_id'] = new_ingredient.ingredient_id

        if ingredient['ingredient_id'] == -1:
            return False

        else:
            return self.add_recipe_ingredient_relation(recipe_id, ingredient)

    def add_recipe_ingredient_relation(self, recipe_id: int, ingredient:dict) -> bool:
        new_rir = RecipeIngredient(recipe_id=recipe_id, ingredient_id=ingredient.get('ingredient_id'), quantity=ingredient.get('quantity'), unit=ingredient.get('unit') )
        db.session.add(new_rir)
        db.session.commit()

        if new_rir.recipeIngredient_id:
            return True
        else:
            return False