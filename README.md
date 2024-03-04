# H2D-Cloud-API
A project for H2D Software

## GET operations
GET operations are read only and do not change any information. Useful for checking license status or fetching customer information.
### Get license information
Returns the license number and whether or not the license is active. `super` or `admin` apikeys can query any license, but customer licenses are limited to self interogation.

* `operation` _(Required)_ - To query a license, `license` should be the operation.
* `apikey` _(Required)_ - Grants access to the API. Provided by H2D Software, LLC.
* `license` OR `account` _(Optional)_ - `super` or `admin` keys can specify which customer account to return information for. If not included, response is based on the apikey holder's account.


Python via requests
```python
import requests

url = "https://h2dcloud.com/api"

payload = {
    "operation": "license",
    "license": "12235",
    "apikey": "123abc",
}

data = requests.get(url, params=payload)
```

cURL from unix shell
```bash
curl --request GET \
  --url 'https://h2dcloud.com/api?apikey=123abc&operation=license&license=12235'
```
Sample response
```json
{
	"data": {
		"cust_active": 1,
		"cust_license": "12235"
	},
	"requestor": "Super Admin",
	"success": true,
	"timestamp": "Sun, 03 Mar 2024 21:17:58 GMT"
}
```
### General query
Returns information based on the MySQL-esque search parameters. Customer keys are limited to self interogation, but `super` and `admin` keys are able to query any account.

* `"operation"` _(Required)_ - To conduct a query, this should be `query`
* `"apikey"` _(Required)_ - The API key provided by H2D Software, LLC.
* `"select"` _(Optional)_ - What data item to select from the database. If omitted, processed as `*`
* `"where"` _(Required)_ - A filter to select a specific account. Should contain both the column name as well as a value. Valid 'where' keys are cust_id, cust_acct, cust_license, key_id, and apikey." See example below

Python via requests
```python
import requests

url = "https://h2dcloud.com/api"

params = {
    "operation": "query",
    "apikey": "123abc",
    "select": "cust_name",
    "where": "cust_license=abc123",
}

data = requests.get(url, params=params)
```
cURL via unix shell
```bash
curl --request GET \
  --url 'https://h2dcloud.com/api?apikey=123abc&operation=query&select=cust_name&where=cust_license%3Dabc123'
```
Sample response
```json
{
	"data": {
		"cust_name": "Best Chiropractic"
	},
	"requestor": "Best Chiropractic",
	"success": true,
	"timestamp": "Sun, 03 Mar 2024 21:50:04 GMT"
}
```

## POST operations
POST transactions are used to alter the database by admin keys. Response indicates success or failure along with the new API key created for the customer.

```json
{
    "operation": <create or update>,
    "data": {
        "cust_acct": "1234",
        "cust_name": "Some Co",
        "cust_license": "12345",
        "cust_active": 0,
        "type": <super,admin,customer>,
    },
    "select": "cust_acct=1234" # for update ops,
    "apikey": "123abc",
}
```

## DELETE operations