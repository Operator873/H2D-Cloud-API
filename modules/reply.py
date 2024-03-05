from datetime import datetime

from flask import jsonify


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
            "timestamp": datetime.now(),
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
                    "type": "customer",
                },
            },
            "timestamp": datetime.now(),
        }
    )


def db_insert_failure(requestor):
    return jsonify(
        {
            "success": False,
            "requestor": requestor,
            "msg": "A failure occured writing to the database. The incident has been logged.",
            "timestamp": datetime.now(),
        }
    )


def successful_creation(requestor, info):
    return jsonify(
        {
            "success": True,
            "requestor": requestor,
            "data": info,
            "timestamp": datetime.now(),
        }
    )
