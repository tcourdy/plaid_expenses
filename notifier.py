import plaid
import json
import os
import calendar
import argparse
from collections import OrderedDict
from datetime import datetime, timedelta
from twilio.rest import Client


parser = argparse.ArgumentParser(usage="If no flags are passed this script will get all of the current months transactions and send them via sms")

parser.add_argument("--print_totals",
                    help="don't send an sms and instead print transactions to the console",
                    action="store_true")

args = parser.parse_args();

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

GRAND_TOTAL_KEY = "Grand Total";

client = plaid.Client(PLAID_CLIENT_ID, PLAID_SECRET, PLAID_PUBLIC_KEY, PLAID_ENVIRONMENT)
with open(EXPENSE_FILE_DIR + "/access_token.txt", "r") as f:
  ACCESS_TOKEN = f.read()

def parse_transactions(expense_dict, transactions):
  """ Returns an ordered dictionary sorted by category amount (with the exception of the grand total key)"""
  grand_total = 0
  for t in transactions:
    grand_total += t['amount']
    category = t['category'][-1]
    if category in expense_dict:
      expense_dict[category] += t['amount'];
    else:
      expense_dict[category] = t['amount'];

  expense_dict = sort_dict_by_value(expense_dict)

  if GRAND_TOTAL_KEY in expense_dict:
    expense_dict[GRAND_TOTAL_KEY] += grand_total
  else:
    expense_dict[GRAND_TOTAL_KEY] = grand_total

  return expense_dict


def sort_dict_by_value(d):
  """Helper function that sorts by category amount(ie: sort by the values of the dictionary passed in)"""
  return OrderedDict(sorted(d.items(), key=lambda x: x[1]))

def send_text(data):
  twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN);
  twilio_client.messages.create(
    #body=json.dumps(data, indent=2),
    body=pretty_print_for_sms(data),
    from_=TWILIO_PHONE_NUMBER,
    to=MY_PHONE_NUMBER
  );


def pretty_print_for_sms(d):
  sms_body = "";
  for i in d.items():
    sms_body += i[0] + ": " + str(i[1]) + "\n"

  return sms_body

def get_monthly_totals():
  """Helper function that will return month to date totals"""
  current_date = datetime.now();
  #returns a tuple of (weekday number of first day of month, num_days_in_month)
  days_in_month = calendar.monthrange(current_date.year, current_date.month);
  start_date = datetime(current_date.year, current_date.month, 1);
  end_date = datetime(current_date.year, current_date.month, days_in_month[1])
  response = client.Transactions.get(ACCESS_TOKEN,
                                     start_date=start_date.strftime("%Y-%m-%d"),
                                     end_date=end_date.strftime("%Y-%m-%d"),
                                     count=500)

  transactions = response['transactions']
  expense_dict = parse_transactions({}, transactions)

  if args.print_totals:
    print("Transactions for %s -  %s" %(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))
    print(json.dumps(expense_dict, indent=2))
  else:
    send_text(expense_dict)


if __name__ == "__main__":
  get_monthly_totals()
