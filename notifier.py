import re
import plaid
from plaid.api import plaid_api
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
import json
import os
import calendar
import smtplib
import argparse
from collections import OrderedDict
from datetime import datetime, timedelta, MINYEAR, MAXYEAR

def valid_date_format(date_str):
  try:
    return datetime.strptime(date_str, "%Y-%m-%d")
  except ValueError:
    msg = "Not a valid date: '{0}'.".format(date_str)
    raise argparse.ArgumentTypeError(msg)

def valid_year(year_str):
  try:
    year_int = int(year_str)
    if year_int > MINYEAR and year_int < MAXYEAR:
      return year_int
    else:
      raise ValueError
  except ValueError:
    msg = "Not a valid year: '{0}' .".format(year_str)
    raise argparse.ArgumentTypeError(msg)

parser = argparse.ArgumentParser(description="Program that uses the plaid api to scrape your bank account's transactions.  You may specify a start_date and and end_date to get a specific date range of transactions if you want something other than the current month")

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

parser.add_argument("--year_to_date_net",
                    help="If this flag is present then print the year to date net total",
                    action="store_true")

parser.add_argument("--current_balance",
                    help="If this flag is present then print the current balance",
                    action="store_true")

parser.add_argument("--monthly_totals_for_year",
                    help="print monthly totals for provided year",
                    type=valid_year,
                    action="store")

args = parser.parse_args();

EXPENSE_FILE_DIR = os.path.dirname(os.path.realpath(__file__));

with open(EXPENSE_FILE_DIR + "/credentials.json", "r") as creds_file:
  creds_dict = json.load(creds_file);

PLAID_CLIENT_ID = creds_dict["plaid_client_id"];
PLAID_SECRET = creds_dict["plaid_secret"];
PLAID_PRODUCTS = "transactions";
PLAID_ENVIRONMENT = plaid.Environment.Development

ACCOUNT_ID = creds_dict["account_id"];

NET_TOTAL_KEY = "Net Total";
TOTAL_EXPENSES_KEY = "Total Expenses";

configuration = plaid.Configuration(
  host = PLAID_ENVIRONMENT,
  api_key = {
    'clientId': PLAID_CLIENT_ID,
    'secret': PLAID_SECRET
  }
)

api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)

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

def get_year_to_date():
  """Function that will return year to date net total"""
  current_date = datetime.now()
  start_date = datetime(current_date.year, 1, 1)
  end_date = datetime(current_date.year, current_date.month, current_date.day)
  transactions = accumulate_transactions(start_date, end_date)
  expense_dict = parse_transactions(transactions)

  print(expense_dict[NET_TOTAL_KEY]);

def get_monthly_totals_for_year():
  """Function that will return monthly totals for provided year"""
  monthly_total_dict = {NET_TOTAL_KEY: 0}
  print("Calculating totals for each month...")
  for x in range(1, 13):
    start_end_tuple = get_start_date_end_date_tuple(args.monthly_totals_for_year, x)
    transactions = accumulate_transactions(start_end_tuple[0], start_end_tuple[1])
    expense_dict = parse_transactions(transactions)
    monthly_total_dict[calendar.month_name[x]] = expense_dict[NET_TOTAL_KEY]
    monthly_total_dict[NET_TOTAL_KEY] = monthly_total_dict[NET_TOTAL_KEY] + expense_dict[NET_TOTAL_KEY]

  print(json.dumps(monthly_total_dict, indent=2))

def get_start_date_end_date_tuple(year, month):
  days_in_month = calendar.monthrange(year, month);
  start_date = datetime(year, month, 1)
  end_date = datetime(year, month, days_in_month[1])
  return (start_date, end_date)

def get_current_balance():
  """Print the current balance of the account"""
  request = AccountsBalanceGetRequest(access_token=ACCESS_TOKEN, options={account_ids:[ACCOUNT_ID]})
  response = client.accounts_balance_get(request)
  print(response["accounts"][0]["balances"]["current"]);

def get_monthly_totals():
  """Helper function that will return month to date totals"""
  if args.start_date:
    start_end_tuple = (args.start_date, args.end_date)
  else:
    current_date = datetime.now();
    start_end_tuple= get_start_date_end_date_tuple(current_date.year, current_date.month)

  transactions = accumulate_transactions(start_end_tuple[0], start_end_tuple[1])
  expense_dict = parse_transactions(transactions);

  expense_dict["DATE_RANGE"] = "%s TO %s" %(start_end_tuple[0].strftime("%Y-%m-%d"), start_end_tuple[1].strftime("%Y-%m-%d"))

  print(json.dumps(expense_dict, indent=2))

def accumulate_transactions(start_date, end_date):
  """Helper function to accumulate all transactions for a date range"""
  request = TransactionsGetRequest(
    access_token = ACCESS_TOKEN,
    start_date = start_date.date(),
    end_date = end_date.date(),
    options = TransactionsGetRequestOptions(
      count = 500,
      account_ids = [ACCOUNT_ID]
    )
  )

  response = client.transactions_get(request)
  transactions = response['transactions']

  while len(transactions) < response['total_transactions']:
    request = TransactionsGetRequest(
      access_token = ACCESS_TOKEN,
      start_date = start_date.strftime("%Y-%m-%d"),
      end_date = end_date.strftime("%Y-%m-%d"),
      options = TransactionsGetRequestOptions(
        count = 500,
        account_ids = [ACCOUNT_ID]
      )
    )
    response = client.transactions_get(request)

    transactions.extend(response['transactions'])

  return transactions;

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

def get_accounts():
  request = AccountsGetRequest(access_token=ACCESS_TOKEN)
  response = client.accounts_get(request)
  print(json.dumps(response.to_dict()["accounts"], indent=2))

if __name__ == "__main__":
  if args.start_date or args.end_date:
    check_valid_date_range()
  if args.year_to_date_net:
    get_year_to_date()
  elif args.current_balance:
    get_current_balance()
  elif args.monthly_totals_for_year:
    get_monthly_totals_for_year()
  else:
    #get_accounts()
    get_monthly_totals()
