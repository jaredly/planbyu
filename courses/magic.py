
from django.template import RequestContext
from django.shortcuts import render_to_response, redirect
from django.http import HttpResponseForbidden, HttpResponseNotFound, HttpResponse
from django.contrib.auth.decorators import login_required

from django.conf.urls import patterns, include, url
import functools
import json

class Router:
    def __init__(self, prefix = '', name_prefix = '', auto_name = True):
        self._prefix = prefix
        self._name_prefix = name_prefix
        self._auto_name = auto_name
        self._patterns = []
        self._subs = {}

    def sub(self, name, *args, **kwds):
        self._subs[name] = Router(*args, **kwds)

    def get_patterns(self):
        result = patterns(self._prefix, *self._patterns)
        for sub in self._subs.values():
            result += sub.get_patterns() 
        return result
    
    def __getattr__(self, name):
        if name in self._subs:
            return self._subs[name]
        raise AttributeError

    def __call__(self, route, kwargs=None, name=None):
        '''This is meant to be used as a decorator.

        NOTE: it does not modify the view in any way, it only adds it to the registry.

        Make sure you place it as the outermost decorator, otherwise the outer decorators will have *no* effect.
        '''
        def decorator(view):
            _name = name
            if _name is None and self._auto_name:
                _name = self._name_prefix + view.__name__.replace('_', '_')
            self._patterns.append(url(route, view, kwargs=kwargs, name=_name))
            return view
        if not isinstance(route, basestring) and callable(route):
            func = route
            route = '^' + func.__name__.replace('_', '_') + '/$'
            return decorator(func)
        return decorator

def jsonview(view):
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        result = view(*args, **kwargs)
        if isinstance(result, dict):
            return HttpResponse(json.dumps(result))
        elif result is None:
            return HttpResponse('{}')
        return result
    return wrapper

def template(name, request_context=True, css=None):
    def decorator(view):
        @functools.wraps(view)
        def wrapper(request, *args, **kwargs):
            response = view(request, *args, **kwargs)
            if isinstance(response, dict):
                _css = css
                if _css:
                    if type(_css) == str:
                        _css = [_css]
                    prefix = STATIC_URL + 'css/'
                    response['extra_css'] = [prefix + cfile for cfile in _css]
                if request_context:
                    return render_to_response(name, response, context_instance=RequestContext(request))
                else:
                    return render_to_response(name, response)
            else: ## elif isinstance(response, HttpResponse):
                return response
            # TODO: should I handle other kinds of return objects?
        wrapper.template = name
        return wrapper
    if not isinstance(name, basestring):
        ## add support for auto-guessing the template name. For example:
        # view 'index' in the 'views.py' for my app 'courses' would be in
        # courses/index.html of the BASE Template dir [which would need to be
        # configured).
        # Similarly, if we have courses/views/some.py with view man() we would
        # have courses/some/man.html
        raise Exception('template name must be a string')
    return decorator

class AjaxException(Exception):
    pass

import inspect
def ajaxview(view):
    '''This does some magic for ajax callbacks.
    1) if the view returns a dict, it is json-dumped into an HttpResponse
    2) arguments (past 'request') are populated from GET.
    2.1) if required arguments are missing, then it returns the JSON
        {'error': 'Missing arguments'}
    3) Any AjaxExceptions throws are output as json: {error: e.message}
    '''
    spec = inspect.getargspec(view)
    minargs = len(spec[0]) - 1
    if spec[-1]:
        minargs -= len(spec[-1])
    view = jsonview(view)
    @functools.wraps(view)
    def wrapper(request): # TODO work with vbls in the url
        # TODO inspect for args that haven't been met (only works if they are
        # contiguous) and grab the remaining out of the GET dict.
        dct = {}
        for i, name in enumerate(spec[0][1:]):
            if name in request.GET:
                dct[name] = request.GET[name]
            elif i < minargs:
                return HttpResponse(json.dumps({'error': 'Missing arguments'}))
        try:
            return view(request, **dct)
        except AjaxException, e:
            return HttpResponse(json.dumps({'error': e.message}))
    wrapper.orig = view
    return wrapper




# vim: et sw=4 sts=4
