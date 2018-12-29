import plaid
import json
import os
import calendar
from datetime import datetime, timedelta
from twilio.rest import Client

EXPENSE_FILE_DIR = os.path.dirname(os.path.realpath(__file__));

with open(EXPENSE_FILE_DIR + "/credentials.json", "r") as creds_file:
  creds_dict = json.load(creds_file);

PLAID_CLIENT_ID = creds_dict["plaid_client_id"];
PLAID_PUBLIC_KEY = creds_dict["plaid_public_key"];
PLAID_SECRET = creds_dict["plaid_secret"];
PLAID_PRODUCTS = "transactions";
PLAID_ENVIRONMENT = "development";

TWILIO_SID = creds_dict["twilio_sid"];
TWILIO_AUTH_TOKEN = creds_dict["twilio_auth_token"];
TWILIO_PHONE_NUMBER = creds_dict["twilio_phone_number"];
MY_PHONE_NUMBER = creds_dict["my_phone_number"];

client = plaid.Client(PLAID_CLIENT_ID, PLAID_SECRET, PLAID_PUBLIC_KEY, PLAID_ENVIRONMENT)
with open(EXPENSE_FILE_DIR + "/access_token.txt", "r") as f:
  ACCESS_TOKEN = f.read()

def get_transactions():
  end_date = datetime.now()
  expense_file_path = EXPENSE_FILE_DIR + "/" + end_date.strftime("%B_%Y") + ".json";

  try:
    expense_file = open(expense_file_path, "r")
    expense_dict = json.load(expense_file);
    expense_file.close();
  except FileNotFoundError:
    expense_dict = {};

  start_date = end_date - timedelta(days=1)
  response = client.Transactions.get(ACCESS_TOKEN,
                                     start_date=start_date.strftime("%Y-%m-%d"),
                                     end_date=end_date.strftime("%Y-%m-%d"),
                                     count=500)

  transactions = response['transactions']

  expense_dict = parseTransactions(expense_dict, transactions);

  with open(expense_file_path, "w+") as fp:
    json.dump(expense_dict, fp, indent=2);

  sendText(expense_dict);


def parseTransactions(expense_dict, transactions):
  grand_total = 0
  for t in transactions:
    grand_total += t['amount']
    category = t['category'][-1]
    if category in expense_dict:
      expense_dict[category] = expense_dict[category] + t['amount'];
    else:
      expense_dict[category] = t['amount'];

  expense_dict["Grand Total"] = grand_total
  return expense_dict

def sendText(data):
  twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN);
  twilio_client.messages.create(
    body=json.dumps(data, indent=2),
    from_=TWILIO_PHONE_NUMBER,
    to=MY_PHONE_NUMBER
  );


def getMonthlyTotals():
  current_date = datetime.now();
  days_in_month = calendar.monthrange(current_date.year, current_date.month); #returns a tuple of (weekday number of first day of month, num_days_in_month)
  start_date = datetime(current_date.year, current_date.month, 1);
  end_date = datetime(current_date.year, current_date.month, days_in_month[1])
  response = client.Transactions.get(ACCESS_TOKEN,
                                     start_date=start_date.strftime("%Y-%m-%d"),
                                     end_date=end_date.strftime("%Y-%m-%d"),
                                     count=500)

  transactions = response['transactions']
  expense_dict = parseTransactions({}, transactions)
  print("Transactions for %s -  %s" %(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))
  print(json.dumps(expense_dict, indent=2))


#not used currently
def list_categories():
  response = client.Categories.get()
  print(json.dumps(response, indent=2))

if __name__ == "__main__":
  get_transactions()
