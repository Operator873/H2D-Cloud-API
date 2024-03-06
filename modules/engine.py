import os
import random
import re
import string
from datetime import datetime

from flask import jsonify

from . import reply
from .h2database import h2db

h2db = h2db()


def log(msg, **kwargs):
    if kwargs.get("id"):
        requestor = h2db.fetch(
            """SELECT cust_name FROM customer WHERE cust_id=%s;""", (kwargs.get("id"),)
        )[0]
    else:
        requestor = "SYSTEM MSG"
    with open(f"{os.getcwd()}/h2dapi.log", "a") as f:
        f.write(f"{datetime.now()} - {requestor} -> {msg}\n")


def get_customer_id(apikey):
    # Fetch key_id with apikey for authentication
    query = """SELECT key_id, key_type FROM apikeys WHERE apikey=%s;"""
    response = h2db.fetch(query, (apikey,))
    return response


def check_key(apikey):
    # Check apikey is valid
    query = """SELECT count(key_id) FROM apikeys WHERE apikey=%s;"""
    return True if h2db.fetch(query, (apikey,))[0] > 0 else False


def get_customer_dict(query_key, query_value):
    query = f"""SELECT * FROM customer JOIN apikeys ON customer.cust_id=apikeys.key_id WHERE customer.{query_key}=%s"""
    return h2db.fetch(query, (query_value,), dictionary=True)


def do_operation(payload, key_id, key_type):
    # Fetch the requestor's account name
    requestor = h2db.fetch(
        """SELECT cust_name FROM customer WHERE cust_id=%s;""", (key_id,)
    )[0]

    # Handle query operations
    if payload.get("operation").lower() == "query":
        # Validate query is well formed
        if not payload.get("where") or not len(payload.get("where").split("=")) == 2:
            return reply.query_help()

        query_key, query_value = payload.get("where").split("=")

        # Verify filter is valid to prevent multiple items
        if query_key not in [
            "cust_id",
            "cust_acct",
            "cust_name",
            "cust_license",
            "key_id",
            "apikey",
        ]:
            return reply.invalid_where_key(requestor)

        info = get_customer_dict(query_key, query_value)

        if not payload.get("select") or payload.get("select") == "*":
            # Process a select all request
            if key_type in ["super", "admin"]:
                # Key is admin, proceed with any transaction
                return reply.return_query(requestor, info)
            else:
                # Handle a select all request from a customer
                if key_id == info["key_id"]:
                    # Verify the customer is self interrogating
                    return reply.return_query(requestor, info)
                else:
                    # Reject customer requests for any other info
                    return reply.query_unauthorized(requestor)
        else:
            # Handle specific selection
            if key_type in ["super", "admin"]:
                # Let admin keys select the info
                return reply.return_query(
                    requestor, {payload.get("select"): info[payload.get("select")]}
                )
            else:
                # Verify customer is self interrogating
                if key_id == info["key_id"]:
                    return reply.return_query(
                        requestor, {payload.get("select"): info[payload.get("select")]}
                    )
                else:
                    # Reject customer requests for any other info
                    return reply.self_interrogation_only(requestor)

    # Handle license operations
    elif payload.get("operation").lower() == "license":
        # Super and Admin type keys can view anything
        if key_type in ["super", "admin"]:
            return reply.return_query(requestor, admin_get_license(payload, key_id))
        else:
            return get_license(payload, key_id)

    # Update operations need to be POST requests. Return an error.
    elif payload.get("operation").lower() in ["update", "create"]:
        return reply.post_required(requestor)

    # Assume error and send a response
    else:
        return reply.empty_help()


def post_operation(payload, key_id):
    # Translate key_id into customer name
    requestor = h2db.fetch(
        """SELECT cust_name FROM customer WHERE cust_id=%s;""", (key_id,)
    )[0]

    # Catch GET operations early
    if payload.get("operation") in ["license", "query"]:
        return reply.use_get_transaction(requestor)

    # Handle new account creations
    elif payload.get("operation") == "create":
        return create_new_account(payload, requestor)

    # Handle account updates
    elif payload.get("operation") == "update":
        return reply.update_account(payload, requestor)

    # Assume error and send a response
    else:
        return reply.empty_post(requestor)


def get_license(payload, key_id):
    customer = get_customer_dict("cust_id", key_id)
    if (
        payload.get("account") == customer["cust_acct"]
        or payload.get("license") == customer["cust_license"]
    ):
        return reply.return_query(
            customer["cust_name"],
            {
                "license": customer["cust_license"],
                "active": customer["cust_active"],
            },
        )
    else:
        return reply.self_interrogation_only(customer["cust_name"])


def admin_get_license(payload, key_id):
    # Verify target info is present or return own license status
    if payload.get("account"):
        query = """SELECT cust_license, cust_active FROM customer WHERE cust_acct=%s"""
        info = h2db.fetch(query, (payload.get("account"),), dictionary=True)
    elif payload.get("license"):
        query = (
            """SELECT cust_license, cust_active FROM customer WHERE cust_license=%s"""
        )
        info = h2db.fetch(query, (payload.get("license"),), dictionary=True)
    else:
        query = """SELECT cust_license, cust_active FROM customer WHERE cust_id=%s"""
        info = h2db.fetch(query, (key_id,), dictionary=True)

    return info


def admin_required(key_id, key_type):
    requestor = h2db.fetch(
        """SELECT cust_name FROM customer WHERE cust_id=%s""", (key_id,)
    )[0]

    return jsonify(
        {
            "success": False,
            "requestor": requestor,
            "msg": f"Key type: {key_type} is not permitted to conduct POST operations.",
            "timestamp": datetime.now(),
        }
    )


def create_new_account(payload, requestor):
    # The new customer information should be inside the data filed
    if "data" not in payload:
        return reply.invalid_create_request(requestor)

    # Verify all required data is present
    new_data = payload.get("data")
    required_keys = ["cust_acct", "cust_name", "cust_license", "cust_active", "type"]

    good_request = True
    for item in required_keys:
        if item not in new_data:
            good_request = False
            break

    # Throw back help if not a valid dataset
    if not good_request:
        return reply.invalid_create_request(requestor)

    # Insert new customer
    query = """INSERT INTO customer VALUES(%s, %s, %s, %s, %s)"""
    args = (
        0,
        new_data["cust_acct"],
        new_data["cust_name"],
        new_data["cust_license"],
        new_data["cust_active"],
    )

    if not h2db.insert(query, args):
        log(f"Database failure: {query} with {args}")
        return reply.db_insert_failure(requestor)

    customer_id = h2db.fetch(
        """SELECT cust_id FROM customer WHERE cust_acct=%s""", (new_data["cust_acct"],)
    )[0]

    if not h2db.insert(
        """INSERT INTO apikeys VALUES(%s, %s, %s)""",
        (customer_id, create_new_apikey(), new_data["type"]),
    ):
        log(f"Database failure: {query} with {args}")
        return reply.db_insert_failure(requestor)

    info = get_customer_dict("cust_id", customer_id)
    return reply.successful_creation(requestor, info)


def update_customer(payload, key_id):
    # Fetch requestor name
    requestor = h2db.fetch(
        """SELECT cust_name FROM customer WHERE cust_id=%s""", (key_id,)
    )[0]

    # If there's no data payload sent, reject
    if not payload.get("data"):
        return reply.invalid_update_request(requestor)

    data = payload.get("data")

    # If the request isn't correctly formatted, reject
    if "update" not in data or "set" not in data:
        return reply.invalid_update_request(requestor)

    # Verify the update selection is valid
    if data["update"].split("=") != 2:
        return reply.invalid_update_request(requestor)

    # Split the update value and select the customer target
    target_column, target_value = data["update"].split("=")
    target = h2db.fetch(
        f"""SELECT cust_id FROM customer WHERE {target_column}="{target_value}";"""
    )[0]

    # Catch no target issues
    if not target:
        return reply.customer_not_found(data, requestor)

    # Give feedback on what, exactly, was updated
    updated_items = []

    # Handle all table changes
    for item in data["set"]:
        if item.startswith("cust") and item.split("=") == 2:
            column, value = item.split("=")
            updated_items.append(column)
            query = f"""UPDATE customer SET {column}="{value}" where cust_id=%s;"""
            h2db.insert(query, (target,))

        if item.startswith("apikey") and item.split("=") == 2:
            column, value = item.split("=")
            updated_items.append(column)
            query = """UPDATE apikeys SET apikey=%s WHERE key_id=%s;"""
            h2db.insert(query, (value, target))

    # Fetch fresh copy of affected customer info
    new_customer = get_customer_dict("cust_id", target)

    return reply.update_customer_confirmation(updated_items, new_customer, requestor)


def create_new_apikey():
    return random.choices(string.ascii_letters + string.digits, k=64)


def help(payload):
    if re.search(r"license", payload.get("help").lower()):
        return jsonify(reply.license_help())
    elif re.search(r"query", payload.get("help").lower()):
        return jsonify(reply.query_help())
    elif re.search(r"update", payload.get("help").lower()):
        return jsonify(reply.update_help())
    else:
        return jsonify(reply.empty_help())
