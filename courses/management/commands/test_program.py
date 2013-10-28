#!/usr/bin/env python

from _get_program import BYUBrowser, parse_program, parse_classes
from _special import args as special

UCORE = 31044

def test_login():
    b = BYUBrowser(*special)
    stuff = b.get_program(UCORE)

def pretty_program(program):
    print 'Program:  %s'%program[0]
    for child in program[2]:
        pretty_requirement(child, 1)

def pretty_requirement(req, ind):
    text = '  '*ind + ' '
    if type(req) == tuple:
        print text + 'Req:', req
    else:
        print text + 'SubReq: %s %d [%s]' % (req['title'], req['min'], req['desc'])
        [pretty_requirement(child, ind+1) for child in req['children']]

def pretty_req(req, ind=0, by='  '):
    if 'cid' in req:
        text = by*ind + {
            None:' ', 'completed':'X', 'planned':'P'}[req['status']]
        text += ' Course: [%s] %s - %s' % (req['name'], req['title'],
                req['credithours'])
        print text
        if req['status'] == 'completed':
            print by*ind + '    Grade: %s; Taken: %s; %s' % (
                    req['grade'], req['semester'], req['comments'])
        elif req['status'] == 'planned':
            print by*ind + '    Planning to take: %s; %s' % (req['semester'], req['comments'])
        for note in req['notes']:
            print by*ind, note
    else:
        print by*ind + 'Requirement "%s" - complete at lease %d out of %d' % (req['title'], req['min'], len(req['children']))
        [pretty_req(child, ind+1, by) for child in req['children']]

def test_parse():
    program = parse_program(open('thestuff.txt').read())
    pretty_program(program)

def test_getclasses():
    b = BYUBrowser(*special)
    text = b.get_classeslist(31044, 78)
    open('classes.html', 'w').write(text)

def test_classes():
    classes = parse_classes(open('others.html').read())
    pretty_req(classes)

def test_through():
    b = BYUBrowser(*special)
    program = b.get_program(UCORE, True)
    print program.pretty()

'''
    child = program.children[0]
    while not type(child) == tuple:
        child = child.children[0]

    classes = b.get_classeslist(*child)
    print classes.pretty()
    '''

if __name__ == '__main__':
    test_through()



# vim: et sw=4 sts=4
