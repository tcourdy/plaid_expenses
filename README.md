Simple python script that uses the plaid api and the twilio api that sends a sms message with the amount of money you have spent broken down by category.  Note that you will need a twilio and plaid developer account to use this

Requirements:
- python3
- pip3
- A credentials.json file with the following structure:
  ```
  {
  "plaid_client_id": "",
  "plaid_public_key": "",
  "plaid_secret": "",
  "twilio_sid": "",
  "twilio_auth_token": "",
  "twilio_phone_number": "",
  "my_phone_number": ""
  }
  ```


After installing the requirements and setting up your `credentials.json` you will need to run `index.py` in order to link your bank account with plaid.

After that you should be able to set `notifier.py` up to run as a daily cron job in order to get daily text messages with the total money you've spent in each category.

Contents of an example sms:
```
{
  "Department Stores": 5.1,
  "Restaurants": 22.44,
  "Parking": 4
}
```
