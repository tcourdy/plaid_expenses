import re
import plaid
import json
import os
import calendar
import smtplib
import argparse
from collections import OrderedDict
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def valid_date_format(date_str):
  try:
    return datetime.strptime(date_str, "%Y-%m-%d")
  except ValueError:
    msg = "Not a valid date: '{0}'.".format(date_str)
    raise argparse.ArgumentTypeError(msg)

parser = argparse.ArgumentParser(description="Program that uses the plaid api to scrape your bank account's transactions.  If you don't use print_totals and no send_method is specified this script will get all of the current months transactions and send them via email.  You may specify a start_date and and end_date to get a specific date range of transactions if you want something other than the current month")

parser.add_argument("--print_totals",
                    help="don't send an sms and instead print transactions to the console",
                    action="store_true")

parser.add_argument("--start_date",
                    help="Format YYYY-MM-DD. The start date of the range of transactions you would like.  If start_date is provided but end_date is not then the default end_date will be 30 days from start_date.  If both start_date and end_date are provided start_date must come before end_date",
                    type=valid_date_format,
                    action="store")

parser.add_argument("--end_date",
                    help="Format YYYY-MM-DD. The end date of the range of transactions you would like.  If end_date is provided but start_date is not then by default start_date will be 30 days prior to end_date.  If start_date is provided along with end_date then end_date must be chronologically after start_date",
                    type=valid_date_format,
                    action="store")

parser.add_argument("--categorize",
                    help="If this flag is present then the transactions will be grouped by category.  Otherwise transactions will be grouped by shop name",
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

EMAIL_ADDRESS_FROM = creds_dict["email_address_from"];
EMAIL_ADDRESS_FROM_PASSWORD = creds_dict["email_address_from_password"];
EMAIL_ADDRESS_TO = creds_dict["email_address_to"];
ACCOUNT_ID = creds_dict["account_id"];

NET_TOTAL_KEY = "Net Total";
TOTAL_EXPENSES_KEY = "Total Expenses";

client = plaid.Client(PLAID_CLIENT_ID, PLAID_SECRET, PLAID_PUBLIC_KEY, PLAID_ENVIRONMENT)
with open(EXPENSE_FILE_DIR + "/access_token.txt", "r") as f:
  ACCESS_TOKEN = f.read()



def check_valid_date_range():
  if args.start_date and args.end_date:
    if args.end_date < args.start_date:
      sys.exit("end_date is before start_date.  Exiting.")
    elif args.start_date > args.end_date:
      sys.exit("start_date is after end_date.  Exiting.")

  if args.start_date and not args.end_date:
    args.end_date = args.start_date + timedelta(days=30)

  if args.end_date and not args.start_date:
    args.start_date = args.end_date - timedelta(days=30)


def get_monthly_totals():
  """Helper function that will return month to date totals"""
  # doesn't matter which one we check see check_valid_date_range function
  if args.start_date:
    start_date = args.start_date
    end_date = args.end_date
  else:
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
  expense_dict = parse_transactions(transactions);

  if args.print_totals:
    print("Transactions for %s -  %s" %(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))
    print(json.dumps(expense_dict, indent=2))
  else:
    send_email(expense_dict)

def parse_transactions(transactions):
  """ Returns an ordered dictionary sorted by category amount (with the exception of the grand total key)"""
  expense_dict = {}
  grand_total = 0
  total_spent = 0
  for t in transactions:
    grand_total += t['amount']
    total_spent += t['amount'] if t['amount'] > 0 else 0

    if args.categorize:
      group_by_category(t, expense_dict)
    else:
      group_by_name(t, expense_dict)

  expense_dict = sort_dict_by_value(expense_dict)
  expense_dict[TOTAL_EXPENSES_KEY] = total_spent
  expense_dict[NET_TOTAL_KEY] = grand_total

  return expense_dict

def group_by_category(transaction, expense_dict):
  """Helper function to help group transactions by category"""
  category = ""
  if transaction["category"] is not None:
    for c in transaction["category"]:
      category += c + ":"

  if category in expense_dict:
    expense_dict[category] += transaction['amount'];
  else:
    expense_dict[category] = transaction['amount'];

# TODO: use a regex to remove dates from names
def group_by_name(transaction, expense_dict):
  """Helper function to help group transactions by shop name"""
  name = transaction["name"] if transaction["name"] is not None else ""
  # remove any dates or digits in the name
  name = re.sub(r'(\d*/\d*|\d*)', "", name).lower()
  if name in expense_dict:
    expense_dict[name] += transaction['amount'];
  else:
    expense_dict[name] = transaction['amount'];

def sort_dict_by_value(d):
  """Helper function that sorts by category amount(ie: sort by the values of the dictionary passed in)"""
  return OrderedDict(sorted(d.items(), key=lambda x: x[1]))

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
  if args.start_date or args.end_date:
    check_valid_date_range()
  get_monthly_totals()
