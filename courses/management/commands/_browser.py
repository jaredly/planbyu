# browser

import urllib2, cookielib, urllib
import bs4

class Browser:
    '''General Class used for screen scraping. Maintains cookie state'''
    def __init__(self):
        self.setup_cookies()

    def setup_cookies(self):
        self.cj = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))
        urllib2.install_opener(opener)

    def get_page(self,url,data={}, header={}):
        if data:
            req = urllib2.Request(url, urllib.urlencode(data), header)
        else:
            req = urllib2.Request(url)
        handle = urllib2.urlopen(req)
        return handle

    def get_soup(self, url, data={}, headers={}):
        print '...loading page', url, data
        return bs4.BeautifulSoup(self.get_page(url, data, headers).read())

def soup_form(form):
    '''Take a form, return a dct with all the hidden values'''
    dct = {}
    for node in form('input'):
        if not node.has_key('name'):
            continue
        dct[node['name']] = node['value']
    return dct

