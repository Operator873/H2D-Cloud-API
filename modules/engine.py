from flask import jsonify
from datetime import datetime
from .h2database import h2db
import re
import os

h2db = h2db()

def log(msg, **kwargs):
    if kwargs.get("id"):
        requestor = h2db.fetch(
            """SELECT cust_name FROM customer WHERE cust_id=%s;""", kwargs.get("id")
        )[0]
    else:
        requestor = ""
    with open(f"{os.getcwd()}/h2dapi.log", "a") as f:
        f.write(f"{datetime.now} - {requestor} -> {msg}")


def get_customer_id(apikey):
    # Fetch key_id with apikey for authentication
    query = """SELECT key_id, key_type FROM apikeys WHERE apikey=%s;"""
    response = h2db.fetch(query, apikey)
    return response


def check_key(apikey):
    # Check apikey is valid
    query = """SELECT count(key_id) FROM apikeys WHERE apikey=%s;"""
    return True if h2db.fetch(query, apikey)[0] > 0 else False


def get_customer_dict(query_key, query_value):
    query = f"""SELECT * FROM customer JOIN apikeys ON customer.cust_id=apikeys.key_id WHERE customer.{query_key}=%s"""
    return h2db.fetch(query, query_value, dictionary=True)


def do_operation(payload, key_id, key_type):
    requestor = h2db.fetch(
        """SELECT cust_name FROM customer WHERE cust_id=%s;""", key_id
    )[0]

    # Handle query operations
    if payload.get("operation").lower() == "query":
        # Validate query is well formed
        if not payload.get("where") or not len(payload.get("where").split("=")) == 2:
            return query_help()

        query_key, query_value = payload.get("where").split("=")
        info = get_customer_dict(query_key, query_value)

        if not payload.get("select") or payload.get("select") == "*":
            # Process a select all request
            if key_type in ["super", "admin"]:
                return {
                    "succsess": True,
                    "requestor": requestor,
                    "data": info,
                    "timestamp": datetime.now(),
                }
            else:
                if key_id == info["key_id"]:
                    return {
                        "success": True,
                        "requestor": requestor,
                        "data": info,
                        "timestamp": datetime.now(),
                    }
                else:
                    return {
                        "success": False,
                        "requestor": requestor,
                        "msg": "This key is limited to self inquires only.",
                        "timestamp": datetime.now(),
                    }

    # Handle license operations
    elif payload.get("operation").lower() == "license":
        # Super and Admin type keys can view anything
        if key_type in ["super", "admin"]:
            return {
                "success": True,
                "requestor": requestor,
                "data": admin_get_license(payload, key_id),
                "timestamp": datetime.now(),
            }
        else:
            return get_license(payload, key_id)

    # Update operations need to be POST requests. Return an error.
    elif payload.get("operation").lower() == "update":
        return {
            "success": False,
            "requestor": requestor,
            "msg": "Update operations should be conducted by POST and only with admin keys.",
            "timestamp": datetime.now(),
        }

    # Assume error and send a response
    else:
        return empty_help()


def get_license(payload, key_id):
    customer = get_customer_dict("cust_id", key_id)
    if (
        payload.get("account") == customer["cust_acct"]
        or payload.get("license") == customer["cust_license"]
    ):
        return {
            "success": True,
            "requestor": customer["cust_name"],
            "data": {
                "license": customer["cust_license"],
                "active": customer["cust_active"],
            },
            "timestamp": datetime.now(),
        }
    else:
        return {
            "success": False,
            "requestor": customer["cust_name"],
            "msg": "This key is limited to self inquires only.",
            "timestamp": datetime.now(),
        }


def admin_get_license(payload, key_id):
    # Verify target info is present or return own license status
    if payload.get("account"):
        query = """SELECT cust_license, cust_active FROM customer WHERE cust_acct=%s"""
        info = h2db.fetch(query, payload.get("account"), dictionary=True)
    elif payload.get("license"):
        query = (
            """SELECT cust_license, cust_active FROM customer WHERE cust_license=%s"""
        )
        info = h2db.fetch(query, payload.get("license"), dictionary=True)
    else:
        query = """SELECT cust_license, cust_active FROM customer WHERE cust_id=%s"""
        info = h2db.fetch(query, key_id, dictionary=True)

    return info


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
        "help": "The query operation returns all customer information based on a search criteria. The results can be filtered with the 'filter' key.",
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
