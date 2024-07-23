import json
import logging
from functools import wraps

import jwt
from flask import request, current_app, Response

from project.database.database import db
from project.database.models import User, Log


def token_required(f):
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
