# Create your views here.
from django.template import RequestContext
from django.shortcuts import render_to_response, redirect
from django.http import HttpResponseForbidden, HttpResponseNotFound, HttpResponse
from django.contrib.auth.decorators import login_required

import functools
import json

from .models import Program, Course, Requirement, SubRequirement, SubCourse, RequirementChild, CourseFlag, Department, Term, sort_flags

from profileme import profile

from magic import Router, template, jsonview, ajaxview, AjaxException

route = Router()
route.sub('ajax', '^ajax/', 'ajax_')

@route('^$')
@template('courses/index.html')
def index(request):
    if request.user.is_anonymous():
        return redirect('/admin/login')
    full_layout = gen_layout(request)
    return { 'layout': full_layout }

@route
@template('courses/planner.html')
def planner(request):
    if request.user.is_anonymous():
        return redirect('/admin/login')
    terms = Term.objects.filter(student=request.user)
    flags = CourseFlag.objects.filter(student=request.user, term=None).exclude(flag='s').exclude(flag='c')
    unorganized = []
    for flag in flags:
        if flag.course not in unorganized:
            flag.course.status_flag(flag)
            unorganized.append(flag.course)
    wflags = CourseFlag.objects.filter(student=request.user, term=None, flag='c')
    waived = []
    for flag in wflags:
        if flag.course not in waived:
            waived.append(flag.course)
    nicenames = 'Winter', 'Spring', 'Summer', 'Fall'
    now = 2012, 3
    next_terms = {}
    for year in range(now[0], now[0]+5):
        for num in range(4):
            if year == now[0] and num < now[1]:
                continue
            next_terms[(year, num)] = ('%d-%d' % (year, num), '%s %d' % (nicenames[num], year))
    for term in terms:
        if next_terms.has_key((term.year, term.termno)):
            del next_terms[(term.year, term.termno)]
    return {'terms': terms,
            'waived': waived,
            'unorganized': unorganized,
            'next_terms':sorted(next_terms.values())}


INDENT = ']]'
HIDENOTDONE = 'hide_notdone'
DEDENT = '[['

# @profile('/home/jared/planbyu.prof')
def gen_layout(request):
    programs = Program.objects.all()
    unrolled = []
    for program in programs:
        program.evaluate(request.user)
        unrolled.append(program)
        unrolled.append(INDENT)
        for child in program.get_children():
            unrolled += unroll(child.get_real())
        unrolled.append(DEDENT)
    return unrolled

def unroll(what):
    if isinstance(what, RequirementChild):
        return unroll(what.get_real())
    if isinstance(what, Course):
        return [what]
    elif isinstance(what, Requirement):
        res = [what, INDENT]
        children = what.get_children()
        if len(children):
            child = children.pop(0).get_real()
            if isinstance(child, Course):
                res.append(HIDENOTDONE)
            res += unroll(child)
        for child in children:
            res += unroll(child.get_real())
        res.append(DEDENT)
        return res
    else:
        raise Exception('unexpected %s while unrolling' % what)

@route.ajax
@ajaxview
def set_flag(request, cid, flag, tid=None):
    if request.user.is_anonymous():
        raise AjaxException('not logged in')
    if flag in ('organized', 'unorganized'):
        flag = 'planned'
    flag = flag[0]

    try:
        cobj = Course.objects.get(cid=cid)
    except Course.DoesNotExist:
        raise AjaxException('Invalid cid')
    CourseFlag.objects.filter(course=cobj).exclude(flag='s').delete()
    if flag != 'n':
        fobj = CourseFlag(course=cobj, student=request.user, flag=flag)
        if tid is not None:
            try:
                year, tno = Term.unshorten(tid)
                term = Term.objects.get(year=year, termno=tno)
            except Term.DoesNotExist:
                raise AjaxException('Invalid term')
            fobj.term = term
        fobj.save()
    return {'success':True}

@route.ajax
@ajaxview
def add_term(request, short):
    if request.user.is_anonymous():
        raise AjaxException('not logged in')
    year, term, termno = Term.unshorten(short)
    termobj = Term(year=year, term=term, termno=termno, student=request.user, past=False)
    termobj.save()
    return {'success':True}

@route.ajax
@ajaxview
def remove_term(request, short):
    if request.user.is_anonymous():
        raise AjaxException('not logged in')
    year, nice, termno = Term.unshorten(short)
    term = Term.objects.get(year=year, termno=termno)
    term.delete()
    return {'success':True}

@route.ajax
@ajaxview
def move_course(request, cid, tid=None):
    if request.user.is_anonymous():
        raise AjaxException('not logged in')
    course = Course.objects.get(cid=cid)
    flags = CourseFlag.objects.filter(course=course, student=request.user).exclude(flag='s')
    flags = sort_flags(list(flags))
    if not flags:
        raise AjaxException('Course not planned')
    for flag in flags[1:]:
        flag.delete()
    if tid:
        try:
            term = Term.byshort(tid)
        except Term.DoesNotExist:
            raise AjaxException('Invalid tid')
        flags[0].term = term
    else:
        flags[0].term = None
    flags[0].save()
    return {'success':True}

@route.ajax
@ajaxview
def star(request, cid):
    try:
        course = Course.objects.get(cid=cid)
    except Course.DoesNotExist:
        raise AjaxException('Invalid cid')
    if not CourseFlag.objects.filter(course=course, student=request.user, flag='s').exists():
        flag = CourseFlag(course=course, student=request.user, flag='s')
        flag.save()
    return {'success':True}

@route.ajax
@ajaxview
def unstar(request, cid):
    try:
        course = Course.objects.get(cid=cid)
    except Course.DoesNotExist:
        raise AjaxException('Invalid cid')
    CourseFlag.objects.filter(course=course, student=request.user, flag='s').delete()
    return {'success':True}


