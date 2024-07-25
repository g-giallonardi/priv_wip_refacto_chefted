from sqlalchemy import ForeignKey, inspect, func
from werkzeug.security import generate_password_hash, check_password_hash

from project.database.database import db

class Serializer(object):

    def serialize(self):
        return {c: getattr(self, c) for c in inspect(self).attrs.keys()}

    @staticmethod
    def serialize_list(l):
        return [m.serialize() for m in l]

class Recipe(db.Model, Serializer):
    __tablename__ = 'recipe'

    recipe_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.String(255))
    diet = db.Column(db.String(50))
    servings = db.Column(db.Integer())
    prepTime = db.Column(db.Integer())
    cookTime = db.Column(db.Integer())
    calories = db.Column(db.Integer())
    carbohydrates = db.Column(db.Integer())
    protein = db.Column(db.Integer())
    fat = db.Column(db.Integer())
    instructions = db.Column(db.ARRAY(db.String), nullable=False)
    breakfast = db.Column(db.Boolean, unique=False, default=False)

    def __repr__(self):
        return f"<Recipe(title='{self.title}', description='{self.description}', diet='{self.diet}')>"

    def serialize(self):
        d = Serializer.serialize(self)
        return d


class MealPlans(db.Model, Serializer):
    __tablename__ = 'meal_plans'

    meal_plan_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey('user.user_id'), nullable=False, index=True)
    user = db.relationship('User', foreign_keys=[user_id])
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)

    def __repr__(self):
        return f"<MealPlan(meal_plan_id='{self.meal_plan_id}'>"

    def serialize(self):
        d = Serializer.serialize(self)
        d['start_date'] = d['start_date'].isoformat()
        d['end_date'] = d['end_date'].isoformat()
        return d


class MealPlanRecipe(db.Model, Serializer):
    __tablename__ = 'meal_plans_recipe_relations'

    meal_plans_recipe_relation_id = db.Column(db.Integer, primary_key=True)
    meal_plan_id = db.Column(db.Integer, ForeignKey('meal_plans.meal_plan_id'), nullable=False, index=True)
    meal_plan = db.relationship('MealPlans', foreign_keys=[meal_plan_id])
    recipe_id = db.Column(db.Integer, ForeignKey('recipe.recipe_id'), nullable=False, index=True)
    recipe = db.relationship('Recipe', foreign_keys=[recipe_id])
    mealType = db.Column(db.String(50))
    date = db.Column(db.Date, nullable=False)

    def __repr__(self):
        return f"<MealPlanRecipe(meal_plan_id='{self.meal_plan_id}', recipe_id='{self.recipe_id}')>"

    def serialize(self):
        d = Serializer.serialize(self)
        d['date'] = d['date'].isoformat()
        return d


class Ingredient(db.Model):
    __tablename__ = 'ingredient'

    ingredient_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    category = db.Column(db.String(100))
    allergen = db.Column(db.String, nullable=True)

    def __repr__(self):
        return f"<Ingredient(name='{self.name}', category='{self.category}')>"

    def serialize(self):
        d = Serializer.serialize(self)
        return d

class RecipeIngredient(db.Model):
    __tablename__ = 'recipe_ingredient_relation'

    recipeIngredient_id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, ForeignKey('recipe.recipe_id'), nullable=False, index=True)
    recipe = db.relationship('Recipe',foreign_keys=[recipe_id])
    ingredient_id = db.Column(db.Integer, ForeignKey('ingredient.ingredient_id'), nullable=False, index=True)
    ingredient = db.relationship('Ingredient', foreign_keys=[ingredient_id])
    quantity = db.Column(db.Float)
    unit = db.Column(db.String(50))

    def __repr__(self):
        return f"<RecipeIngredient(recipe_id='{self.recipe_id}', ingredient_id='{self.ingredient_id}')>"

    def serialize(self):
        d = Serializer.serialize(self)
        return d

class User(db.Model):
    __tablename__ = 'user'

    user_id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(100))
    first_name = db.Column(db.String(100))
    email = db.Column(db.String(200), unique=True)
    password_hash = db.Column(db.String(200))
    birthdate = db.Column(db.Date)
    gender = db.Column(db.Integer) # 0 Male, 1 Female, 2 Non-binary, 3 Other, 4 won't say it
    dietaryPreference = db.Column(db.String, server_default='flex')
    allergies = db.Column(db.ARRAY(db.String))
    goals = db.Column(db.Integer)
    tokenCount = db.Column(db.Integer, default=10, nullable=False)
    lastTokenReset = db.Column(db.DateTime, server_default=func.now())
    joinDate = db.Column(db.DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<User(id='{self.user_id}', email='{self.email}')>"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def serialize(self):
        d = Serializer.serialize(self)
        del d['password_hash']
        del d['joinDate']
        del d['lastTokenReset']
        d['birthdate'] = d['birthdate'].isoformat()
        return d

class Log(db.Model):
    __tablename__ = 'logs'

    log_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey('user.user_id'), nullable=False, index=True)
    user = db.relationship('User', foreign_keys=[user_id])
    url = db.Column(db.Text, nullable=False)
    method = db.Column(db.String(25), nullable=False)
    args = db.Column(db.Text, nullable=True)
    status_code = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Log(id='{self.log_id}', user='{self.user_id}')>"
