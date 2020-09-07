import plaid
from flask import Flask
from flask import render_template
from flask import request
from flask import jsonify

with open(EXPENSE_FILE_DIR + "/credentials.json", "r") as creds_file:
  creds_dict = json.load(creds_file);

PLAID_CLIENT_ID = creds_dict["plaid_client_id"];
PLAID_PUBLIC_KEY = creds_dict["plaid_public_key"];
PLAID_SECRET = creds_dict["plaid_secret"];
PLAID_PRODUCTS = "transactions"
PLAID_ENVIRONMENT = "development"

app = Flask(__name__)

client = plaid.Client(PLAID_CLIENT_ID, PLAID_SECRET, PLAID_PUBLIC_KEY, PLAID_ENVIRONMENT)

@app.route('/')
def index():
  return render_template(
    'index.html',
    plaid_public_key=PLAID_PUBLIC_KEY,
    plaid_environment=PLAID_ENVIRONMENT,
    plaid_products=PLAID_PRODUCTS,
  )

@app.route("/get_access_token", methods=['POST'])
def get_access_token():
  public_token = request.form['public_token']
  exchange_response = client.Item.public_token.exchange(public_token)
  access_token = exchange_response['access_token']
  write_access_token_to_file(access_token)
  return jsonify(exchange_response)

def write_access_token_to_file(access_token):
  f = open('access_token.txt', 'w')
  f.write(access_token)
  f.close()

if __name__ == "__main__":
  app.run(port=8000)
