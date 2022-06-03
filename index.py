import plaid
from plaid.api import plaid_api
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.country_code import CountryCode

import json
import uuid

from flask import Flask
from flask import render_template
from flask import request
from flask import jsonify

with open("credentials.json", "r") as creds_file:
  creds_dict = json.load(creds_file)

CLIENT_NAME = "plaid_expenses"
PLAID_CLIENT_ID = creds_dict["plaid_client_id"]
PLAID_SECRET = creds_dict["plaid_secret"]
PLAID_PRODUCTS = "transactions"
PLAID_ENVIRONMENT = "development"

app = Flask(__name__)

configuration = plaid.Configuration(
  host=plaid.Environment.Development,
  api_key={
    'clientId': PLAID_CLIENT_ID,
    'secret': PLAID_SECRET,
  }
)

api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)

@app.route('/')
def index():
  return render_template(
    'index.html',
    plaid_environment=PLAID_ENVIRONMENT,
    plaid_products=PLAID_PRODUCTS,
  )

@app.route("/exchange_public_token", methods=['POST'])
def get_access_token():
  public_token = request.get_json()["public_token"]
  plaid_request = ItemPublicTokenExchangeRequest(
    public_token=public_token
  )
  response = client.item_public_token_exchange(plaid_request)
  access_token = response['access_token']
  write_access_token_to_file(access_token)
  return jsonify(response.to_dict())

@app.route("/create_link_token", methods=['POST'])
def create_link_token():
  print("im in create link token")
  client_user_id = str(uuid.uuid4())
  request = LinkTokenCreateRequest(
    products = [Products(PLAID_PRODUCTS)],
    client_name = "test app",
    country_codes = [CountryCode("US")],
    language = "en",
    user=LinkTokenCreateRequestUser(client_user_id=client_user_id)
  )
  response = client.link_token_create(request)

  return jsonify(response.to_dict())

def write_access_token_to_file(access_token):
  f = open('access_token.txt', 'w')
  f.write(access_token)
  f.close()

if __name__ == "__main__":
  app.run(port=8000)
