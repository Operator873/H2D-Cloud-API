#!/usr/bin/python3

from flask import Flask, jsonify, request
from waitress import serve

from modules.h2database import h2db

h2d = Flask(__name__)
db = h2db()

# Handle GET requests
@h2d.route("/api", methods=["GET"])
def api_get():
    return (
        jsonify(
            {
                "success": False,
                "msg": "This API is under development and not yet functional.",
            }
        ),
        200,
    )


# Handle POST requests
@h2d.route("/api", methods=["POST"])
def api_post():
    pass


# Handle DELETE requests
@h2d.route("/api", methods=["DELETE"])
def api_del():
    pass


if __name__ == "__main__":
    serve(h2d, host="0.0.0.0", port=32023)
