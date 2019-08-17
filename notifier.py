import plaid
import json
import os
import calendar
import smtplib
import argparse
from collections import OrderedDict
from datetime import datetime, timedelta
from twilio.rest import Client
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

parser = argparse.ArgumentParser(usage="If you don't use print_totals and no send_method is specified this script will get all of the current months transactions and send them via email")

parser.add_argument("--print_totals",
                    help="don't send an sms and instead print transactions to the console",
                    action="store_true")
parser.add_argument("--send_method",
                    help="specify either email or sms",
                    choices=["email", "sms"],
                    default="email",
                    action="store")

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

EMAIL_ADDRESS_FROM = creds_dict["email_address_from"];
EMAIL_ADDRESS_FROM_PASSWORD = creds_dict["email_address_from_password"];
EMAIL_ADDRESS_TO = creds_dict["email_address_to"];
ACCOUNT_ID = creds_dict["account_id"];

NET_TOTAL_KEY = "Net Total";
TOTAL_EXPENSES_KEY = "Total Expenses";

client = plaid.Client(PLAID_CLIENT_ID, PLAID_SECRET, PLAID_PUBLIC_KEY, PLAID_ENVIRONMENT)
with open(EXPENSE_FILE_DIR + "/access_token.txt", "r") as f:
  ACCESS_TOKEN = f.read()


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
                                     account_ids=[ACCOUNT_ID],
                                     count=500)

  transactions = response['transactions']
  expense_dict = parse_transactions(transactions)

  if args.print_totals:
    print("Transactions for %s -  %s" %(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))
    print(json.dumps(expense_dict, indent=2))
  elif args.send_method == "email":
    send_email(expense_dict)
  elif args.send_method == "sms":
    send_sms(expense_dict)


def parse_transactions(transactions):
  """ Returns an ordered dictionary sorted by category amount (with the exception of the grand total key)"""
  expense_dict = {}
  grand_total = 0
  total_spent = 0
  for t in transactions:
    grand_total += t['amount']
    total_spent += t['amount'] if t['amount'] > 0 else 0
    category = ""
    for c in t['category']:
      category += c + ":"
    if category in expense_dict:
      expense_dict[category] += t['amount'];
    else:
      expense_dict[category] = t['amount'];

  expense_dict = sort_dict_by_value(expense_dict)
  expense_dict[TOTAL_EXPENSES_KEY] = total_spent
  expense_dict[NET_TOTAL_KEY] = grand_total

  return expense_dict


def sort_dict_by_value(d):
  """Helper function that sorts by category amount(ie: sort by the values of the dictionary passed in)"""
  return OrderedDict(sorted(d.items(), key=lambda x: x[1]))

def send_sms(data):
  twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN);
  twilio_client.messages.create(
    body=pretty_print_data(data),
    from_=TWILIO_PHONE_NUMBER,
    to=MY_PHONE_NUMBER
  );

def send_email(data):
  server = smtplib.SMTP('smtp.gmail.com', 587)
  server.starttls()
  server.login(EMAIL_ADDRESS_FROM, EMAIL_ADDRESS_FROM_PASSWORD)
  message = create_email_message(data)
  server.send_message(message)
  server.quit()

def create_email_message(d):
  msg = MIMEMultipart()
  msg['From']=EMAIL_ADDRESS_FROM
  msg['To']=EMAIL_ADDRESS_TO
  msg['Subject']="Yesterday's Expenses"
  body = pretty_print_data(d);
  msg.attach(MIMEText(body, 'plain'))
  return msg

def pretty_print_data(d):
  sms_body = "";
  for i in d.items():
    sms_body += i[0] + ": " + str(i[1]) + "\n"

  return sms_body

if __name__ == "__main__":
  get_monthly_totals()
