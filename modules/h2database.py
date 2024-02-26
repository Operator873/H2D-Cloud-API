import os
from configparser import ConfigParser
from datetime import datetime

import mysql.connector


class h2db:
    def __init__(self):
        # Read local configuration file for better security
        self.cnf = ConfigParser()
        self.cnf.read(f"{os.getcwd()}/modules/db.conf")

    def connect(self):
        # Connect to MySQL Database and return connection
        return mysql.connector.connect(
            host=self.cnf["mysql"]["server"],
            user=self.cnf["mysql"]["user"],
            password=self.cnf["mysql"]["pass"],
            database=self.cnf["mysql"]["database"],
        )

    def fetch(self, query, args, quantity="one"):
        # Connect to the database and get a cursor
        db = self.connect()
        c = db.cursor()

        try:
            if args:
                # If the query was supplied with args, handle those
                c.execute(query, args)
            else:
                # Else handle as a standard SQL query (not ideal)
                c.execute(query)

            # Return one or all responses
            response = {
                "success": True,
                "data": c.fetchone() if quantity == "one" else c.fetchall(),
            }

        except Exception as e:
            # If an error is encountered, return the information
            response = {
                "success": False,
                "data": str(e),
            }

        finally:
            # Disconnect from the database and return the query results
            db.disconnect()
            return response
