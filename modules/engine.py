import os
import re
import random
import string
from datetime import datetime

from flask import jsonify

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
            return query_help()

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
            return invalid_where_key(requestor)

        info = get_customer_dict(query_key, query_value)

        if not payload.get("select") or payload.get("select") == "*":
            # Process a select all request
            if key_type in ["super", "admin"]:
                # Key is admin, proceed with any transaction
                return return_query(requestor, info)
            else:
                # Handle a select all request from a customer
                if key_id == info["key_id"]:
                    # Verify the customer is self interrogating
                    return return_query(requestor, info)
                else:
                    # Reject customer requests for any other info
                    return query_unauthorized(requestor)
        else:
            # Handle specific selection
            if key_type in ["super", "admin"]:
                # Let admin keys select the info
                return return_query(
                    requestor, {payload.get("select"): info[payload.get("select")]}
                )
            else:
                # Verify customer is self interrogating
                if key_id == info["key_id"]:
                    return return_query(
                        requestor, {payload.get("select"): info[payload.get("select")]}
                    )
                else:
                    # Reject customer requests for any other info
                    return self_interrogation_only(requestor)

    # Handle license operations
    elif payload.get("operation").lower() == "license":
        # Super and Admin type keys can view anything
        if key_type in ["super", "admin"]:
            return return_query(requestor, admin_get_license(payload, key_id))
        else:
            return get_license(payload, key_id)

    # Update operations need to be POST requests. Return an error.
    elif payload.get("operation").lower() in ["update", "create"]:
        return post_required(requestor)

    # Assume error and send a response
    else:
        return empty_help()


def post_operation(payload, key_id):
    # Translate key_id into customer name
    requestor = h2db.fetch(
        """SELECT cust_name FROM customer WHERE cust_id=%s;""", (key_id,)
    )[0]

    # Catch GET operations early
    if payload.get("operation") in ['license', 'query']:
        return use_get_transaction(requestor)
    
    # Handle new account creations
    elif payload.get("operation") == "create":
        return create_new_account(payload, requestor)
    
    # Handle account updates
    elif payload.get("operation") == "update":
        return update_account(payload, requestor)
    
    # Assume error and send a response
    else:
        return empty_post(requestor)


def get_license(payload, key_id):
    customer = get_customer_dict("cust_id", key_id)
    if (
        payload.get("account") == customer["cust_acct"]
        or payload.get("license") == customer["cust_license"]
    ):
        return return_query(
            customer["cust_name"],
            {
                "license": customer["cust_license"],
                "active": customer["cust_active"],
            },
        )
    else:
        return self_interrogation_only(customer["cust_name"])


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
            "timestamp": datetime.now()
        }
    )


def create_new_account(payload, requestor):
    # The new customer information should be inside the data filed
    if "data" not in payload:
        return invalid_create_request(requestor)
    
    # Verify all required data is present
    new_data = payload.get("data")
    required_keys = ['cust_acct', 'cust_name', 'cust_license', 'cust_active', 'type']

    good_request = True
    for item in required_keys:
        if item not in new_data:
            good_request = False
            break
    
    # Throw back help if not a valid dataset
    if not good_request:
        return invalid_create_request(requestor)
    
    # Insert new customer
    query = """INSERT INTO customer VALUES(%s, %s, %s, %s, %s)"""
    args = (0, new_data["cust_acct"], new_data["cust_name"], new_data["cust_license"], new_data['cust_active'])
    
    if not h2db.insert(query, args):
        log(f"Database failure: {query} with {args}")
        return db_insert_failure(requestor)
    
    customer_id = h2db.fetch(
        """SELECT cust_id FROM customer WHERE cust_acct=%s""", (new_data["cust_acct"],)
    )[0]

    if not h2db.insert(
        """INSERT INTO apikeys VALUES(%s, %s, %s)""", (customer_id, create_new_apikey(), new_data["type"])
    ):
        log(f"Database failure: {query} with {args}")
        return db_insert_failure(requestor)
    
    info = get_customer_dict("cust_id", customer_id)
    return successful_creation(requestor, info)


def create_new_apikey():
    return random.choices(string.ascii_letters + string.digits, k=64)


def help(payload):
    if re.search(r"license", payload.get("help").lower()):
        return jsonify(license_help())
    elif re.search(r"query", payload.get("help").lower()):
        return jsonify(query_help())
    elif re.search(r"update", payload.get("help").lower()):
        return jsonify(update_help())
    else:
        return jsonify(empty_help())


def license_help():
    return {
        "success": True,
        "help": "The license operation returns the license and license status. If no 'license' or 'account' is supplied, returns the status of the license associated with the apikey.",
        "example": {"operation": "license", "apikey": "abc1234", "license": "1234dcba"},
        "timestamp": datetime.now(),
    }


def query_help():
    return {
        "success": True,
        "help": "The query operation returns all customer information based on a MySQL search style transaction.",
        "example": {
            "operation": "query",
            "apikey": "abc1234",
            "select": ["cust_name", "cust_license"],
            "where": "account=00123",
        },
        "timestamp": datetime.now(),
    }


def update_help():
    return {
        "success": True,
        "help": "The update operation requires an admin or higher access apikey. This allows customer information or license status to be changed.",
        "example": {
            "operation": "update",
            "apikey": "abc1234",
            "cust_acct": "001234",
            "set": "cust_active=1",
        },
        "timestamp": datetime.now(),
    }


def empty_help():
    return {
        "success": False,
        "msg": "Your transaction was either not valid or badly formed. Try sending a GET request for specific help. See example...",
        "example": {"help": "query", "apikey": "abc1234"},
        "timestamp": datetime.now(),
    }


def no_api_key():
    return jsonify(
        {
            "success": False,
            "msg": "This API requires an apikey.",
            "example": {"operation": "help", "apikey": "abc1234"},
            "timestamp": datetime.now(),
        }
    )


def invalid_key():
    return jsonify(
        {
            "success": False,
            "msg": "The API key supplied is not valid.",
            "timestamp": datetime.now(),
        }
    )


def invalid_where_key(requestor):
    return jsonify(
        {
            "success": False,
            "requestor": requestor,
            "msg": "Valid 'where' keys are cust_id, cust_acct, cust_name, cust_license, key_id, and apikey.",
            "timestamp": datetime.now(),
        }
    )


def return_query(requestor, data):
    return jsonify(
        {
            "success": True,
            "requestor": requestor,
            "data": data,
            "timestamp": datetime.now(),
        }
    )


def query_unauthorized(requestor):
    return jsonify(
        {
            "success": False,
            "requestor": requestor,
            "msg": "This key is limited to self inquires only.",
            "timestamp": datetime.now(),
        }
    )


def self_interrogation_only(requestor):
    return jsonify(
        {
            "success": False,
            "requestor": requestor,
            "msg": "This key is limited to self inquires only.",
            "timestamp": datetime.now(),
        }
    )


def post_required(requestor):
    return jsonify(
        {
            "success": False,
            "requestor": requestor,
            "msg": "Update or create operations should be conducted by POST and only with admin keys.",
            "timestamp": datetime.now(),
        }
    )


def use_get_transaction(requestor):
    return jsonify(
        {
            "success": False,
            "requestor": requestor,
            "msg": "Query or License operations should be conducted via a GET request.",
            "timestamp": datetime.now(),
        }
    )


def empty_post(requestor):
    return jsonify(
        {
            "success": False,
            "requestor": requestor,
            "msg": "POST requests can be used to create or update customer information. These transactions are only available to admin keys.",
            "timestamp": datetime.now()
        }
    )


def invalid_create_request(requestor):
    return jsonify(
        {
            "success": False,
            "requestpr": requestor,
            "msg": "In order to create a new customer account, you must supply the required information. See example.",
            "example": {
                "operation": "create",
                "apikey": "abc1234",
                "data": {
                    "cust_acct": 10001,
                    "cust_name": "Example Customer",
                    "cust_license": "1234abcd",
                    "cust_active": 1,
                    "type": "customer"
                }
            },
            "timestamp": datetime.now()
        }
    )


def db_insert_failure(requestor):
    return jsonify(
        {
            "success": False,
            "requestor": requestor,
            "msg": "A failure occured writing to the database. The incident has been logged.",
            "timestamp": datetime.now()
        }
    )


def successful_creation(requestor, info):
    return jsonify(
        {
            "success": True,
            "requestor": requestor,
            "data": info,
            "timestamp": datetime.now()
        }
    )