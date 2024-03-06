#!/usr/bin/python3

from flask import Flask, jsonify, request
from waitress import serve

import modules.engine as engine


def handle_query(payload):
    pass


def main():
    h2d = Flask(__name__)
    h2d.json.sort_keys = False

    # Handle GET requests
    @h2d.route("/api", methods=["GET"])
    def api_get():
        # Before anything else, log unique connection information
        log_data = f"""IP: {request.environ["HTTP_X_FORWARDED_FOR"]} - UA: {request.headers.get("User-Agent")}"""
        engine.log(log_data)

        # Refuse connections with no apikey
        if "apikey" not in request.args:
            engine.log("No API key provided. Transaction declined.")
            return engine.no_api_key(), 401

        # Validate key
        if not engine.check_key(request.args.get("apikey")):
            engine.log("Invalid API key provided.")
            return engine.invalid_key(), 401

        # Seems like we have a good user. Fetch the key's info, log the transaction
        key_id, key_type = engine.get_customer_id(request.args.get("apikey"))
        engine.log(request.args, id=key_id)

        # Respond to help requests, regardless of key type
        if "help" in request.args:
            return engine.help(request.args), 200

        # Respond to queries conditionally on info requested
        elif "operation" in request.args:
            return engine.do_operation(request.args, key_id, key_type), 200

        # Respond to everything else
        else:
            return jsonify(engine.empty_help()), 200

    # Handle POST requests
    @h2d.route("/api", methods=["POST"])
    def api_post():
        # Before anything else, log unique connection information
        log_data = f"IP: {request.environ["HTTP_X_FORWARDED_FOR"]} - UA: {request.headers.get("User-Agent")}"
        engine.log(log_data)

        # Refuse connections with no apikey
        if "apikey" not in request.args:
            engine.log("No API key provided. Transaction declined.")
            return engine.no_api_key(), 401

        # Validate key
        if not engine.check_key(request.args.get("apikey")):
            engine.log("Invalid API key provided.")
            return engine.invalid_key(), 401

        # Seems like we have a good user. Fetch the key's info
        key_id, key_type = engine.get_customer_id(request.args.get("apikey"))

        # POST transactions should only be attempted by admin keys
        if key_type not in ['super', 'admin']:
            engine.log("POST transaction attempted by unauthorized key.")
            return engine.admin_required(key_id, key_type)
        
        # Log the transaction
        engine.log(request.args, id=key_id)

        if "operation" in request.args:
            return engine.post_operation(request.args, key_id), 200
        
        # Catch any other POST otherwise not handled
        else:
            return jsonify(engine.empty_help()), 200

    # Handle DELETE requests
    @h2d.route("/api", methods=["DELETE"])
    def api_del():
        pass

    serve(h2d, host="0.0.0.0", port=32023)


if __name__ == "__main__":
    main()
