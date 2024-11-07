from datetime import date

from database.models import MealPlans


class MealPlanManager:
    def __init__(self):
        self.today = date.today()

    def get_meal_plans(self) -> list:
        meal_plan_raws = MealPlans.objects.all()

        return meal_plan_raws.serialize()