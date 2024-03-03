#!/usr/bin/python3

from flask import Flask, jsonify, request
from waitress import serve

from modules.h2database import h2db
import modules.engine as engine

"""
Flow of operations
1) Check apikey validity
2) Determine key access level
3) Determine desired operation
4) Determine if key access level is valid for desired operation.
5) Conduct operation
6) Valid result
7) Send response


Incoming payload
{
    "operation": {license, query, update},
    "apikey": <apikey>,
    <other keys as needed>: <data>,
}

Help payload

{
    "help": "{license, query, update}",
    "apikey": Optional,
}
"""


def handle_query(payload):
    pass


def main():
    h2d = Flask(__name__)

    # Handle GET requests
    @h2d.route("/api", methods=["GET"])
    def api_get():
        # Refuse connections with no apikey
        if "apikey" not in request.args:
            return engine.no_api_key(), 401

        # Validate key
        if not engine.check_key(request.args.get("apikey")):
            return engine.invalid_key(), 401

        # Seems like we have a good user. Fetch the key's info, log the transaction
        key_id, key_type = engine.get_customer_id(request.args.get("apikey"))
        engine.log(request.args, id=key_id)

        # Respond to help requests, regardless of key type
        if "help" in request.args:
            return engine.help(request.args), 200

        # Respond to queries conditionally on info requested
        if "operation" in request.args:
            return engine.do_operation(request.args, key_id, key_type), 200

    # Handle POST requests
    @h2d.route("/api", methods=["POST"])
    def api_post():
        pass

    # Handle DELETE requests
    @h2d.route("/api", methods=["DELETE"])
    def api_del():
        pass

    serve(h2d, host="0.0.0.0", port=32023)


if __name__ == "__main__":
    main()
