import json
import logging
from functools import wraps

import jwt
from flask import request, current_app, Response

from project.database.database import db
from project.database.models import User, Log
from project.utils.UserManager import UserManager


def token_required(f):
    """
    Decorator method for token authentication.

    :param f: The function to be decorated.
    :return: The decorated function.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]
        if not token:
            return {
                "message": "Authentication Token is missing!",
                "data": None,
                "error": "Unauthorized"
            }, 401
        try:
            data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
            current_user = User.query.filter_by(user_id=data["user_id"]).first()
            if current_user is None:
                return {
                    "message": "Invalid Authentication token!",
                    "data": None,
                    "error": "Unauthorized"
                }, 401
        except Exception as e:
            print(e)
            logging.error(e)
            return {
                "message": "Something went wrong",
                "data": None,
                "error": str(e)
            }, 500

        return f(current_user, *args, **kwargs)

    return decorated


def log_endpoint_access(f):
    """
    :param f: The function to be decorated with logging functionality.
    :return: The decorated function that logs endpoint access.

    The `log_endpoint_access` function is a decorator that can be used to add logging functionality to an endpoint function in a Flask application. It logs various details of the endpoint
    * access, such as the user, URL, HTTP method, and arguments.

    Usage example:

    ```python
    @app.route('/example_endpoint', methods=['POST'])
    @log_endpoint_access
    def example_endpoint(user, data):
        # Endpoint code here
        return jsonify({'message': 'Endpoint accessed successfully'})
    ```

    When the `example_endpoint` function is called, the `log_endpoint_access` decorator will log information about the access and store it in the database.

    Note: Make sure that the `db` object is properly configured and imported before using the `log_endpoint_access` decorator.

    """
    @wraps(f)
    def decorated(*args, **kwargs):
        args_repr = [a for a in args]
        endpoint_data = request.json if request.method != "GET" else None
        log_data = {
            'user': args_repr[0],
            'url': request.url,
            'method': request.method,
            'args': json.dumps(endpoint_data)
        }

        kwargs_dict = {}
        for k, v in kwargs.items():
            kwargs_dict[k] = v

        try:
            result = f(args_repr[0], kwargs_dict)
            result_data = result.data
            log_data["status_code"] = json.dumps(result.status_code)
        except Exception as e:
            print(e)
            logging.error(e)
            result_data = {'error':500}
            log_data["status_code"] = 500

        new_log = Log(**log_data)
        db.session.add(new_log)
        db.session.commit()

        result_data = json.dumps(result_data) if isinstance(result_data, dict) else result_data
        return Response(
            result_data, status=log_data["status_code"], mimetype='application/json'
        )

    return decorated

def pay_action_cost(cost):
    """
    :param cost: The cost of the action that needs to be paid.
    :return: A decorator function that can be used to add functionality to the decorated function.

    This method is a decorator function that adds the ability to pay the cost of an action before executing the decorated function. It checks if the user has enough tokens to cover the cost
    * of the action and deducts the cost from the user's token count if they do. If the user does not have enough tokens, it returns an error response.

    Example usage:

    @pay_action_cost(10)
    def perform_action(user_id):
        # Code to perform the action
        pass

    In this example, the `perform_action` function will only be executed if the user has at least 10 tokens. If they don't, an error response will be returned instead.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Pre-decoration logic
            sign_user = args[0]
            user = User.query.filter(User.user_id == sign_user.user_id).first()
            current_token = user.tokenCount
            if current_token >= cost:
                user.tokenCount -= cost
                db.session.commit()
            else:
                return Response(
                    {'error':'No more action token available'}, status=403, mimetype='application/json'
                )
            # result = args(*args, **kwargs)
            # # Post-decoration logic
            return func(*args, **kwargs)
        return wrapper
    return decorator
