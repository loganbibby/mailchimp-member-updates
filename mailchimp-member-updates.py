import sys
import os.path
import time
import logging
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
# 3rd party
import cfgparse
import requests
import prettytable

class Config: pass
config = Config()

# Pull in configuration file
c = cfgparse.ConfigParser()
c.add_option('log_filename', type='string')
c.add_option('debug', type='int')
c.add_option('runfile', type='string')
c.add_option('apikey', dest='mailchimp_apikey', keys='MAILCHIMP', type='string')
c.add_option('baseurl', dest='mailchimp_baseurl', keys='MAILCHIMP', type='string')
c.add_option('dc', dest='mailchimp_dc', keys='MAILCHIMP', type='string')
c.add_option('defaultsender', dest='mail_defaultsender', keys='MAIL', type='string')
c.add_option('server', dest='mail_server', keys='MAIL', type='string', default='localhost')
c.add_option('port', dest='mail_port', keys='MAIL', type='int', default=25)
c.add_option('use_tls', dest='mail_use_tls', keys='MAIL', type='choice', choices=['1', '0'], default='0')
c.add_option('use_ssl', dest='mail_use_ssl', keys='MAIL', type='choice', choices=['1', '0'], default='0')
c.add_option('username', dest='mail_username', keys='MAIL', type='string')
c.add_option('password', dest='mail_password', keys='MAIL', type='string')
c.add_option('timeout', dest='mail_timeout', keys='MAIL', type='int', default=30)
c.add_option('template', dest='mail_template', keys='MAIL', type='string')
c.add_file('config.ini')

for key, value in c.parse().__dict__.iteritems():
    key = key.upper()

    if key == 'DEBUG' or not hasattr(config, key):
        setattr(config, key, value)

# setup logging
log_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

if config.DEBUG:
    log_level = logging.DEBUG
else:
    log_level = logging.INFO

logger.setLevel(log_level)

log_file_handler = logging.FileHandler('%s' % (config.LOG_FILENAME), 'a')
log_file_handler.setFormatter(log_formatter)
log_file_handler.setLevel(log_level)
logger.addHandler(log_file_handler)

if config.DEBUG:
    log_stream_handler = logging.StreamHandler(sys.stdout)
    log_stream_handler.setLevel(log_level)
    log_stream_handler.setFormatter(log_formatter)
    logger.addHandler(log_stream_handler)

logger.debug('Logging engaged!')

# set Mailchimp base URL
setattr(config, 'MAILCHIMP_BASEURL', config.MAILCHIMP_BASEURL.format(dc=config.MAILCHIMP_DC))
logger.debug('Mailchimp base URL set to %s' % config.MAILCHIMP_BASEURL)

# load lists
with open('lists.json', 'r') as fh:
    lists = json.load(fh)
    logger.debug('%d lists loaded' % len(lists))

# establish connection with SMTP server
try:
    s = smtplib.SMTP(config.MAIL_SERVER, config.MAIL_PORT, timeout=config.MAIL_TIMEOUT)
    logger.debug('Connected successfully to %s:%s within %d seconds' % (config.MAIL_SERVER, config.MAIL_PORT, config.MAIL_TIMEOUT))
except socket.timeout, e:
    logger.error('Connection to %s timed out after %d seconds' % (config.MAIL_SERVER, config.MAIL_TIMEOUT))
    raise e
except smtplib.SMTPConnectError, e:
    logger.error('Connection to %s failed: %s' % (config.MAIL_SERVER, e))
    raise e

if config.MAIL_USERNAME:
    try:
        s.login(config.MAIL_USERNAME, config.MAIL_PASSWORD)
        logger.debug('Successful login for %s' % config.MAIL_USERNAME)
    except smtplib.SMTPHeloError, e:
        logger.error('Server did not respond to HELO greeting properly')
        raise e
    except smtplib.SMTPAuthenticationError, e:
        logger.error('The server didn\'t accept the username/password combination.')
        raise e
    except smtplib.SMTPException, e:
        logger.error('No suitable authentication method was found.')
        raise e

for listid, options in lists.iteritems():
    # look for a runfile to see when last run was.
    runfile = config.RUNFILE.format(listid=listid)
    logger.debug('Runfile name: %s' % runfile)

    try:
        since = os.path.getmtime(runfile)
        logger.debug('Last run timestamp is %s' % since)
    except OSError:
        since = 0
        logger.debug('No runfile, using the epoch as the timestamp')

    with open(runfile, 'w') as fh:
        fh.write(' ')
        logger.debug('Updated runfile')

    since = datetime.fromtimestamp(since)

    mailchimp_url = '%s/export/1.0/list?apikey=%s&id=%s&since=%s' % (config.MAILCHIMP_BASEURL, config.MAILCHIMP_APIKEY, listid, since.strftime('%Y-%m-%d'))
    logger.debug('GET request to %s' % mailchimp_url)
    r = requests.get(mailchimp_url)

    members = r.text.splitlines(True)

    table = prettytable.PrettyTable(json.loads(members.pop(0)))

    logger.debug('%d members returned' % len(members))

    for member in members:
        member = json.loads(member)
        table.add_row(member)

    # We don't want the last 16 columns (they're not useful for syncing data)
    columns_to_remove = range(len(table.field_names)-16, len(table.field_names))
    columns_to_remove.reverse()
    for i in columns_to_remove:
        table.field_names.pop(i)

    if len(members) <= 0:
        logger.info('No members updated for list %s, not sending an empty e-mail because that\'s rude' % listid)
        continue

    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Updates to the %s mailing list' % options['listname']
    msg['From'] = config.MAIL_DEFAULTSENDER
    msg['To'] = ', '.join(options['recipients'])

    with open(config.MAIL_TEMPLATE, 'r') as fh:
        html = ''.join(fh.readlines())

    html = html.format(
        mailinglist=options['listname'],
        date=since.strftime('%m/%d/%Y'),
        table=table.get_html_string(),
        listid=listid
        )

    msg.attach(MIMEText(html, 'html'))

    try:
        s.sendmail(config.MAIL_DEFAULTSENDER, options['recipients'], msg.as_string())
        logger.info('Email sent to %s' % ', '.join(recipients))
    except smtplib.SMTPRecipientsRefused, e:
        logger.error('All recipients were refused. Nobody got the mail. %s' % e.recipients)
    except smtplib.SMTPHeloError, e:
        logger.error('The server didn\'t reply properly to the HELO greeting. Closing connection and ending script.')
        s.quit()
        raise e
    except smtplib.SMTPSenderRefused, e:
        logger.error('The server didn\'t accept "%s" as the sender. Closing connection and ending script.' % config.MAIL_DEFAULTSENDER)
        s.quit()
        raise e
    except smtplib.SMTPDataError, e:
        logger.error('The server replied with an unexpected error code: %s' % e)

s.quit()
logger.debug('Closed connection to SMTP server')
