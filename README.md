Simple python script that uses the plaid api to send an sms message with the amount of money you have spent broken down by category (keeps a running total for each month).  Note that you will need a plaid developer account to use this.  I set up a dummy gmail account and turned off secure features in order to successfully send an email from this python script.

Requirements:
- python3
- pip3
- A credentials.json file with the following structure:
  ```
  {
  "plaid_client_id": "",
  "plaid_public_key": "",
  "plaid_secret": "",
  "email_address_from": "",
  "email_address_from_password": "",
  "email_address_to": "",
  "account_id": ""
  }
  ```


After installing the requirements and setting up your `credentials.json` you will need to run `index.py` in order to link your bank account with plaid.

After that you should be able to set `notifier.py` up to run as a daily cron job in order to get daily text messages with the total money you've spent in each category.

Contents of an example email:
```
{
  "Department Stores": 5.1,
  "Restaurants": 22.44,
  "Parking": 4
}
```
