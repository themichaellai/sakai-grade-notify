import mechanize
from bs4 import BeautifulSoup
import getpass
import re
import hashlib
import sys
from datetime import datetime
import time
import smtplib

EMAIL_USER = ''
EMAIL_PASS = ''
USERNAME = ''
PASSWORD = ''
VERBOSE = 0
SLEEP_MINS = 30
if len(sys.argv) > 1:
  try: VERBOSE = int(sys.argv[1])
  except: VERBOSE = 0

def timeStr():
  return datetime.now().strftime('%I:%M%p')

def emailNotify(gb):
  the_time = timeStr()
  if VERBOSE >= 1: print '%s Sending mail to: %s' % (the_time, EMAIL_USER)
  header = 'To: %s\nFrom: %s\nSubject: %s grade change - %s\n\n' % (EMAIL_USER, EMAIL_USER, gb['name'], the_time)
  msg = 'Your grades for %s have changed at %s!\nCheck them at %s' % (gb['name'], the_time, gb['link'])
  serv = smtplib.SMTP('smtp.gmail.com:587')
  serv.starttls()
  serv.login(EMAIL_USER, EMAIL_PASS)
  serv.sendmail(EMAIL_USER, EMAIL_USER, header + msg)
  serv.quit()

if __name__ == '__main__':
  USERNAME = raw_input('username: ')
  # Sakai password
  PASSWORD = getpass.getpass()
  
  # determine whether should send email or not
  send_email = raw_input('send email? (y/n)')
  if send_email == 'y':
    send_email = True
    EMAIL_USER = raw_input('Username: ')
    EMAIL_PASS = getpass.getpass()
  else: send_email = False

  # init browser
  br = mechanize.Browser()
  # sakai prevents bots
  br.set_handle_robots(False)

  # login (doesn't check for incorrect login, so be careful
  br.open('https://sakai.duke.edu/portal/clogin')
  if VERBOSE == 1: print timeStr(), 'Logging in...'
  if VERBOSE == 2: print timeStr(), br.title()
  br.select_form(nr=0)
  br['j_username'] = USERNAME
  br['j_password'] = PASSWORD
  login_response = br.submit()

  # do the redirect manually
  br.select_form(nr=0)
  login_response2 = br.submit()
  if VERBOSE == 2: print timeStr(), br.title()

  # get the links to all the classpages from the header of homepage
  homepage = BeautifulSoup(login_response2.read())
  header = homepage.find_all(class_='termContainer')[1]
  header = BeautifulSoup(str(header))
  class_links = header.find_all('a')

  # populate list of dictionaries of class names, gradebook links, and grade hashes
  # grades are hashed so don't have to as string
  gradebook_links = []
  class_name_re = re.compile('(?<=: )(?P<class_name>.*?)(?= :)')
  for l in class_links: 
    br.open(l.get('href'))
    class_name = class_name_re.search(br.title()).group('class_name')
    if VERBOSE == 1: print timeStr(), 'getting:', class_name
    if VERBOSE == 2: print timeStr(), br.title()
    res = br.follow_link(text_regex=r'Gradebook')
    if VERBOSE == 2: print timeStr(), br.title()
    outer_soup = BeautifulSoup(res.read())
    frame_link = outer_soup.find_all('iframe', class_='portletMainIframe')[0].get('src')
    if VERBOSE == 2: print timeStr(), frame_link
    res = br.open(frame_link)

    gradebook = BeautifulSoup(res.read())
    #print gradebook.prettify()
    table = gradebook.find_all(class_='listHier')[0]
    table = BeautifulSoup(str(table))
    grades = str(table.find_all('tbody')[0])
    gradebook_links.append({
      'name': class_name,
      'link': res.geturl(),
      'content': int(hashlib.md5(grades).hexdigest(), 16),
    })

  while 1:
    if VERBOSE >= 1: print timeStr(), 'sleeping for', str(SLEEP_MINS) + '...'
    time.sleep(SLEEP_MINS * 60)
    for gb in gradebook_links:
      res = br.open(gb['link'])
      if VERBOSE >= 1: print timeStr(), 'getting:', gb['name']
      gradebook = BeautifulSoup(res.read())
      table = gradebook.find_all(class_='listHier')[0]
      table = BeautifulSoup(str(table))
      grades = str(table.find_all('tbody')[0])
      grades_hash = int(hashlib.md5(grades).hexdigest(), 16)
      if gb['content'] != grades_hash:
        if VERBOSE >= 1: print timeStr(), gb['name'], 'grades changed!'
        if send_email: emailNotify(gb)
        gb['content'] = grades_hash
      else:
        if VERBOSE >= 1: print timeStr(), 'no change', gb['name']
