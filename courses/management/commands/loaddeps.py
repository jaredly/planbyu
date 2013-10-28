#!/usr/bin/env python

from django.core.management.base import BaseCommand, CommandError
from _get_program import BYUBrowser
from _browser import soup_form
from _special import args as special

import urllib
import re

class Command(BaseCommand):
    # todo: make it logon and download the file itself.
    args = ''
    help = 'Grab the department listing from BYU'

    def handle(self, *args, **options):
        depts = get_depts()
        for code, title in depts:
            save_dept(code, title)

try:
    from courses import models
except:
    models = False

def save_dept(code, title):
    try:
        old = models.Department.objects.get(code=code)
    except models.Department.DoesNotExist:
        newd = models.Department(did=0, code=code, long_name=title)
        newd.save()

URL = 'https://gamma.byu.edu/ry/ae/prod/registration/cgi/regOfferings.cgi'
def get_depts():
    '''Gets the departments from gamma.byu.edu and yields

        CODE, Friendly Name
    '''
    b = BYUBrowser(special[0], special[1], URL)
    page = b.get_soup(URL)
    newpage = b.get_soup(page.find('a')['href'])
    ## open('loeein.html', 'w').write(page.prettify().encode('utf8'))

    form = newpage.find('form', {'name': 'RegOptions'})
    target = form['action']
    dct = soup_form(form)
    script = newpage.find(text=re.compile('window\.brownie'))
    brownie = re.findall("window\.brownie = '([^']+)'", script)[0]
    dct['brownie'] = brownie
    dct['YearTerm'] = '20125'
    dct['e'] = '@YearTerm'
    dct['parms'] = '20125'
    dct['c'] = 'regOfferings'

    real = b.get_soup(URL, dct)
    options = real.find('select', {'name': 'Department'})('option')
    for option in options:
        if option['value'] == '*':
            continue
        long_name = option.string.strip()
        # the long_name is generally prefixed by the code. strip it.
        if long_name.startswith(option['value'] + ' - '):
            long_name = long_name[len(option['value'] + ' - '):].strip()
        yield option['value'], long_name

if __name__ == '__main__':
    get_depts()




# vim: et sw=4 sts=4
