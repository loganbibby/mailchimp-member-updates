# Mailchimp member updates
Python cron script to retrieve updated members and e-mail them to select recipients. 

## Prerequisites
The package was developed under Python 2.7.6 on a Mac and currently runs on CentOS 6.4 using Python 2.7.9.

The package requires:
* cfgparse
* prettytable
* requests

You can easily install these using pip by running `pip install -r requirements.txt` while inside the root directory.

## Configuration
There's three total configuration files: config.ini, email.html, and lists.json.

### config.ini
`[DEFAULT]`
`log_filename`: The file to save the log to.
`debug`: Indicates if debug mode is enabled. Enabling it gives you more verbose and console logging.
`runfile`: What to call your runfiles. Use the `{listid}` as a placeholder for the list's Mailchimp ID.

`[MAIL]`
`server`: SMTP server hostname. Defaults to _localhost_.
`port`: SMTP server port. Defaults to _25_.
`username`: If you require SMTP authentication, this is the username.
`password`: Password for SMTP authenication.
`defaultsender`: From e-mail address.
`template`: Name of file to use as the e-mail template. See next section for placeholders.

`[MAILCHIMP]`
`apikey`: The Mailchimp API key you can create and find [here](https://admin.mailchimp.com/account/api/), minus your datacenter.
`dc`: The Mailchimp datacenter you're assigned to. They API key has it at the end: _apikey_-_datacenter_. For instance, mine is us7.
`baseurl`: The API's base URL. Defaults to _http://{dc}.api.mailchimp.com_ and unless you have a good reason to change it, leave it.

### email.html
A simple HTML document with placeholders for mailing list information. This will be used to send your e-mail updates.

Use `{mailinglist}` as a placeholder for the friendly mailinglist name. `{date}` for the date in %m/%d/%Y format. `{table}` for the HTML table of new or updated members. `{listid}` for the Mailchimp list ID.

### lists.json
A simple JSON file of your lists and a couple of options. It should be formatted as so:
```
{
  "MailchimpListID": {
    "listname": "Your Friendly Name",
    "recipients": ["you@example.com", "them@example.com"]
  }
}
```

You can find your list ID on the "List Name and Defaults" page fo your list. Right column, very top. 
