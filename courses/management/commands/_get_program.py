#!/usr/bin/env python

from _browser import Browser
from bs4 import BeautifulSoup
import urllib
import bs4
import re
try:
    from _special import args as special
except ImportError as e:
    print '''No _special found. Did you forget to create it?
# special
args = ('username', 'password')
'''
    raise e

TESTING = False

try:
    from courses import models
except:
    models = None

http_header = {
    "User-Agent" : "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.46 Safari/535.11",
    "Accept" : "text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,text/png,*/*;q=0.5",
    "Accept-Language" : "en-us,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Content-type": "application/x-www-form-urlencoded",
    "Host" : "imos.ldschurch.org",
    "Referer" : "",
}

class BYUBrowser(Browser):
    programurl = 'https://home.byu.edu/webapp/mymap/plan.htm?programId=%0.5d'
    classesurl = 'https://home.byu.edu/webapp/mymap//plan/selectClasses.htm'
    initlogin = 'https://cas.byu.edu/cas/login?service='
    mainrest = urllib.unquote('https%3A%2F%2Fhome.byu.edu%2Fwebapp%2Fmymap%2Flogin%3Bjsessionid%3D28601dd609ec636357b1e1cf436a.m1%3Bjsessionidversion%3D%2Fwebapp%2Fmymap%3A0')
    def __init__(self, uname, pwd, url=mainrest):
        Browser.__init__(self)
        self.login(uname, pwd, url)

    def login(self, user, pwd, url=mainrest):
        '''Login to MyMAP

        Arugments:
            user(str): username
            pwd(str) : password

        '''
        self.get_page(self.programurl % 0)
        page = self.get_soup(self.initlogin + urllib.quote(url, ''))

        form = page.find('form', id='credentials')
        
        action = form['action']
        dct = {}
        dct['username'] = user
        dct['password'] = pwd
        dct['warn'] = 'false'
        dct['_eventId'] = 'submit'
        dct['execution'] = form.find('input', {'name':'execution'})['value']
        dct['lt'] = form.find('input', {'name':'lt'})['value']
        self.get_page(self.initlogin, dct)

    def get_program_page(self, pid):
        return self.get_soup(self.programurl % pid)

    def get_program(self, pid, courses=True):
        page = self.get_program_page(pid)
        program = parse_program(pid, page)
        if pid and courses:
            program.load_courses(self)
        return program

    def get_classeslist_page(self, pid, gid):
        dct = {}
        dct['programId'] = pid
        dct['groupNumber'] = gid
        return self.get_soup(self.classesurl, dct)

    def get_classeslist(self, pid, gid):
        page = self.get_classeslist_page(pid, gid)
        return parse_classes(page)

class Program:
    def __init__(self, title, webid, intid, children):
        self.title = title
        self.webid = webid
        self.intid = intid
        self.children = children
        self.loaded = False

    def __repr__(self):
        return self.title + ':%s' % self.webid

    def load_courses(self, browser):
        if self.loaded:
            raise Exception('already loaded classes')
        for i in range(len(self.children)):
            child = self.children[i]
            if type(child) == tuple:
                # it's a course listing
                self.children[i] = browser.get_classeslist(*child)
            else:
                # it's a sub requirement
                child.load_courses(browser)
            if TESTING:
                self.children = [self.children[i]]
                break
        self.loaded = True

    def pretty(self, ind=0):
        text = ' '*ind + 'Program: %s [#%d]\n' % (self.title, self.webid)
        for child in self.children:
            if type(child) == tuple:
                text += ' '*ind + '  %s\n' % (child,)
            else:
                text += child.pretty(ind+2)
        return text

    def save(self, user):
        node = models.Program(title=self.title, pid=self.webid,
                internal_id=self.intid)
        node.save()
        print 'saving', self.title, self.webid
        for child in self.children:
            print 'child', child
            cnode = child.save(user, node)
            if cnode:
                node.children.add(cnode)
        node.save()
        return node

class RequirementGroup:
    def __init__(self, title, desc, children=None):
        self.title = title
        self.desc = desc
        self.children = children or []
        self.count = 0
        self.loaded = False

    def __repr__(self):
        return self.title

    def load_courses(self, browser):
        if self.loaded:
            raise Exception('already loaded')
        olds = self.children
        self.children = []
        for child in olds:
            self.children.append(browser.get_classeslist(*child))
            if TESTING:
                break
        # # # self.children = [browser.get_classeslist(*child) for child
                # # in self.children]
        self.loaded = True

    def pretty(self, ind=0):
        text = ' '*ind + 'Group: %s :: %s\n' % (self.title, self.desc)
        for child in self.children:
            if type(child) == tuple:
                text += ' '*ind + '  %s\n' % (child,)
            else:
                text += child.pretty(ind+4)
        return text

    def save(self, user, program):
        self.count = len(self.children)
        node = models.Requirement(title=self.title, description=self.desc,
                count=self.count, rtype='normal')
        node.save()
        for child in self.children:
            cnode = child.save(user, program)
            if cnode:
                node.children.add(cnode)
        node.save()
        cnode = models.SubRequirement()
        cnode.real = node
        cnode.save()
        return cnode

class Requirement:
    def __init__(self, title, desc, count, rtype, children=None):
        self.title = title
        self.desc = desc
        self.count = count
        self.rtype = rtype
        self.children = children or []

    def __repr__(self):
        return self.title+' : '+self.desc

    def pretty(self, ind=0):
        text = ' '*ind + '[%s] Complete ' % self.title
        if self.rtype == 'normal':
            text += '%d of %d; %s\n' % (
                self.count, len(self.children), self.desc)
        elif self.rtype == 'hours':
            text += '%d hours; %s\n' % (self.count, self.desc)
        elif self.rtype == 'maxhours':
            text += 'up to %d hours; %s\n' % (self.count, self.desc)
        else:
            raise Exception('invalid req type: %s, %s, %s' % (self.rtype,
                self.title, self.desc))
        for child in self.children:
            text += child.pretty(ind+4)
        return text

    def save(self, user, program):
        node = models.Requirement(title=self.title, description=self.desc,
                count=self.count, rtype=self.rtype)
        node.save()
        for child in self.children:
            cnode = child.save(user, program)
            if cnode:
                node.children.add(cnode)
        node.save()
        cnode = models.SubRequirement()
        cnode.real = node
        cnode.save()
        return cnode

class Course:
    def __init__(self, cid, dept, num, title, notes, credithours):
        self.cid = cid
        self.dept = dept
        self.num = num
        self.title = title
        self.notes = notes
        self.credithours = credithours
        self.status = ' '
        self.semester = None
        self.grade = None
        self.comments = None

    def pretty(self, ind=0):
        text = ' '*ind + '[%s] Course: [%s %s] %s - %s\n' % (self.status,
                self.dept, self.num, self.title, self.credithours)
        if self.status=='P':
            text += ' '*ind + '      Planned [%s] - %s\n' % (self.semester, self.comments)
        elif self.status == 'C':
            text += ' '*ind + '      Completed. grade: %s [%s] - %s\n' % (
                    self.grade, self.semester, self.comments)
        elif self.status == ' ':
            pass
        elif self.status == 'R':
            text += ' '*ind + '      Registered [%s] - %s\n' % (self.semester, self.comments)
        else:
            raise Exception('invalid course status: %s; %s' % (self.name +
                self.title, self.status))
        for note in self.notes:
            text += ' '*ind + '      + %s\n' % note
        return text

    def save(self, user, program, sub=True):
        try:
            node = models.Course.objects.get(cid=self.cid)
            if not node.program or node.program.type() != 'major' and program and program.type == 'major':
                node.program = program
                node.save()
        except models.Course.DoesNotExist:
            node = models.Course(num=self.num, cid=self.cid,
                    long_name=self.title, description='',
                    credithours = self.credithours, notes='\n'.join(self.notes),
                    honors=(self.dept=='HONRS' or self.num.endswith('/H')), program=program)
            try:
                node.department = models.Department.objects.get(code=self.dept)
            except models.Department.DoesNotExist:
                return None
                # raise Exception('Course %s with unknown department: %s' %
                #        (self.pretty(), self.dept))
            node.save()
        ## save a flag
        if self.status != ' ':
            self.save_flag(user, node)
        if sub:
            cnode = models.SubCourse()
            cnode.real = node
            cnode.save()
            return cnode

    def save_flag(self, user, node):
        flag = models.CourseFlag(course=node, student=user, grade=self.grade, comments=self.comments)
        if self.semester:
            term = self.semester[0]
            year = self.semester[1]
            order = ['winter', 'spring', 'summer', 'fall']
            termno = order.index(self.semester[0])
            try:
                # todo add past checkint
                termo = models.Term.objects.get(year=year, termno=termno, student=user)
            except models.Term.DoesNotExist:
                termo = models.Term(year=year, termno=termno, student=user, term=term)
                termo.save()
            flag.term = termo
        else:
            flag.term = None
        flag.flag = self.status.lower()
        flag.save()


def parse_program(webid, page):
    '''Parse the main program page at
    https://home.byu.edu/webapp/mymap/plan.htm?programId=31044

    reqirement is either:
        {'title': str, children: [pid, sid]}
    or:
        [pid, sid]
    Depending on whether the program has subdvisions

    returns title, code[internal int], requirements[][]
    '''

    title = page.find(text=re.compile("^Selected Program"))
    title = title.split(':')[1].strip()
    if webid == 0:
        code = '00000'
    else:
        code = page.find(text=re.compile("^Program Code")).split(':')[1].strip()
    options = [(option['value'], option.string)
            for option in page.find(id='programList')('option')]
    print 'Courses Available:', options
    tables = page('table', 'application')
    if webid == 0:
        courses = []
        for table in tables:
            courses += parse_inline(table)
        return courses
    if len(tables) == 1:
        reqs = parse_table(tables[0])
    else:
        reqs = []
        for table in tables:
            reqs += parse_table(table) 
    return Program(title, webid, code, reqs)

def parse_inline(table):
    trs = table('tr', 'programCourse')
    courses = []
    for tr in trs:
        course = parse_course(tr)
        courses.append(course)
        '''
        link = int(tr.find('a')['name'].split('_')[0])
        code = tr.find('span', 'courseName').string.split()
        num = code[-1]
        dept = ' '.join(code[:-1])
        title = tr.find('span', 'transcriptTitle').string
        '''
    return courses


def parse_table(table):
    '''Get the requirements out of a
    <table class="application">

    returns: [Requirement, ...]
    '''

    groups = table('tr', 'requirement header')
    results = []
    if groups:
        # sub categories...
        for group in groups:
            result = RequirementGroup(group.td.a.text, 
                    group.td.find(text=re.compile(' - Complete')))
            for tr in group.next_siblings:
                if isinstance(tr, bs4.NavigableString) or tr.name != 'tr':
                    continue
                if tr in groups:
                    break
                appbutton = tr('input', 'appButton mymapAction')
                if not appbutton:
                    continue
                result.children.append(parse_button(appbutton[0]))
            result.min = len(result.children) # all must be completed
            results.append(result)
    else:
        for button in table('input', 'appButton mymapAction'):
            results.append(parse_button(button))
    return results

def parse_button(button):
    text = button['onclick'].split('(')[1].split(')')[0].split(', ')
    pid = int(text[0].strip("'"))
    sid = int(text[1].strip("'"))
    return pid, sid

def parse_classes(page):
    rows = page.table.tbody('tr')
    parent = parse_row(rows[0])
    last = parent
    for row in rows[1:]:
        if not row.has_key('class') or 'requirement' not in row['class']:
            if not row('a'):
                # not a course
                continue
            last.children.append(parse_course(row))
        else:
            num = row['class'][0][len('requirementHeader'):].split('.')
            cparent = parent
            while len(num)>2:
                cparent = cparent.children[int(num.pop(1))-1]
            last = parse_row(row)
            cparent.children.append(last)
    return parent

def parse_course(row):
    td = row.td
    cid = int(re.findall('\d+', td.find('a')['href'])[0])
    name = td.find('span', 'courseName').string.split()
    num = name[-1]
    dept = ' '.join(name[:-1]).strip()
    del name
    title = td.find('span', 'transcriptTitle').string
    notes = [(p.string or '') for p in td('p')]
    tds = row('td')
    credithours = tds[1].string.rstrip('v')
    credithours = float(credithours)
    course = Course(cid, dept, num, title, notes, credithours)
    if len(tds) >= 4 and tds[3].span:
        comments = ''.join(tds[3].span.strings).strip()
        course.comments = comments
        course.semester = findsem(comments)
        ## TODO: make it check for failed courses...
        if comments.startswith('Completed') or comments.startswith('Planned - Completed') or comments.startswith('Course Waived'):
            course.status = 'C'
            course.grade = tds[2].string
        elif comments.startswith('Registered') or comments.startswith('Planned - Registered'):
            course.status = 'R'
        elif comments.startswith('Planned'):
            course.status = 'P'
        else:
            print '!![][] unrecognized comment: ', comments
    return course

def findsem(text):
    '''Find the semester a course was completed or planned'''
    parts = text.split('-')
    for part in reversed(parts):
        if part.strip().split()[0].lower() in ('fall', 'winter', 'spring', 'summer'):
            sem, year = part.strip().lower().split()
            return sem, int(year)
    return None

RTYPES = {
    'hours': re.compile('^ - Complete (\d+(\.\d+)?) hours'),
    'maxhours': re.compile('^ - Complete up to (\d+(\.\d+)?) hours'),
    'normal': re.compile('^ - Complete (\d+) (of \d+ )?(Options?|requirements?|courses?)'),
}

def parse_row(row):
    title = row.td.span.a.string
    desc = row.td.span.find(text=re.compile('^ - Complete'))
    rtype = None
    for rt, regex in RTYPES.iteritems():
        m = regex.match(desc)
        if m:
            count = float(m.groups()[0])
            rtype = rt
            break
    if not rtype:
        raise Exception('unknown requirement type found: [%s] %s' % (title, desc))
    return Requirement(title, desc, count, rtype)

# vim: et sw=4 sts=4
