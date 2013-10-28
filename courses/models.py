from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _

from listfield import ListField

class ModelBase(models.Model):
    @property
    def classname(self):
        return self.__class__.__name__

    class Meta:
        abstract = True

def make_long_choices(*items):
    res = []
    used = []
    for item in items:
        res.append((item.lower().replace(' ', '_'), _(item)) )
    return res

def make_choices(*items):
    res = []
    used = []
    for item in items:
        if '^' in item:
            c = item[item.find('^')+1]
            item = item.replace('^', '')
        else:
            c = item[0]
        c = c.lower()
        if c in used:
            raise Exception('Multiple use of the same character: %s - %s' % (c, item))
        used.append(c)
        res.append((c, _(item)) )
    return res

class Department(ModelBase):
    did = models.IntegerField()
    code = models.CharField(max_length=10)
    long_name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.long_name

def sort_flags(flags):
    return sorted(flags, (lambda f, g: cmp(FLAG_ORDER.index(f.flag),
                                FLAG_ORDER.index(g.flag))))


class Course(ModelBase):
    department = models.ForeignKey(Department)
    num = models.CharField(max_length=20)
    cid = models.PositiveIntegerField()
    ## TODO do I need to worry about title codes?
    long_name = models.CharField(max_length=100)
    description = models.TextField()
    honors = models.BooleanField()
    credithours = models.PositiveIntegerField()
    notes = models.TextField()
    # TODO allow one course to be part of multiple programs
    program = models.ForeignKey('Program', blank=True, null=True)
    
    def code(self):
        return '%s %s' % (self.department.code, self.num)
    
    def program_type(self):
        if self.program:
            return self.program.type()
        return 'elective'

    def evaluate(self, user):
        '''Determine the status based on the given user.

        Look at all the CourseFlags, and sets the "status" and "starred" attrs.
        '''
        if hasattr(self, 'status'):
            return
        flags = list(CourseFlag.objects.filter(course=self, student=user).all())
        flags = sort_flags(flags)
        
        if not flags:
            self.status = 'notdone'
        else:
            self.status_flag(flags[0])

        self.starred = False
        for flag in flags:
            if flag.flag == 's':
                self.starred = True

    def status_flag(self, flag):
        if flag.flag == 's':
            self.status = 'notdone'
        elif flag.flag == 'c':
            self.status = 'completed'
        elif flag.flag == 'r':
            self.status = 'registered'
        elif flag.flag == 'p':
            if flag.term is not None:
                self.status = 'organized'
            else:
                self.status = 'unorganized'

    def flag_tags(self):
        if not hasattr(self, 'flags'):
            return ''
        return ' '.join(k for k in self.flags if self.flags[k])

    def __unicode__(self):
        return u'%s %s : %s' % (self.department.code, self.num, self.long_name)

class RequirementChild(ModelBase):
    realchild = None
    really = None

    def __unicode__(self):
        return self.find_realchild().__unicode__()

    def get_real(self):
        if not self.really:
            self.really = self.find_realchild().real
        return self.really

    def find_realchild(self):
        if not self.realchild:
            try:
                self.realchild = self.subrequirement
            except SubRequirement.DoesNotExist:
                try:
                    self.realchild = self.subcourse
                except SubCourse.DoesNotExist:
                    raise Exception('must be subclassed...')
        return self.realchild

class SubRequirement(RequirementChild):
    real = models.ForeignKey('Requirement')

    def __unicode__(self):
        return '[req] ' + self.real.__unicode__()

class SubCourse(RequirementChild):
    real = models.ForeignKey(Course)

    def __unicode__(self):
        return '[course] ' + self.real.__unicode__()

def bestflag(flags):
    best = None
    fstart = [f[0] for f in FLAGS]
    for flag in flags:
        i = fstart.index(flag)
        if best is None or i < best:
            best = i
    if best is None:
        return False
    return best

RTYPES = make_choices(
    'Hours',
    'Max Hours',
    'Normal'
)

class Requirement(ModelBase):
    title = models.CharField(max_length=100)
    description = models.TextField()
    count = models.PositiveIntegerField(
            help_text='the count - could be (max) number of hours'
                'or the number of courses '
                'or the number of options to fill')
    rtype = models.CharField(max_length=1, choices=RTYPES)
    children = models.ManyToManyField(RequirementChild)

    def __unicode__(self):
        return self.title + ' ' + self.description

    cache_children = False
    def get_children(self):
        if not self.cache_children:
            self.cache_children = list(self.children.all())
        return self.cache_children

    def program(self):
        if hasattr(self, '_program'):
            return self._program
        # TODO make this a cached value in the db
        parent = self.subrequirement_set.all()[0]
        if parent.program_set.count()>0:
            self._program = parent.program_set.all()[0]
        else:
            self._program = parent.requirement_set.all()[0].program()
        return self._program

    def evaluate(self, user):
        '''Determine the status based on the given user.

        sets the following cached variables to be referenced by the
        template:

        self.short_status(str) overall - completed, registered, etc.
        self.full_status(str[]) for each "chunk" (course or credit hour)
            what is the status?
        self.starred(int) number of courses starred
        '''
        self.evaluated = True
        if hasattr(self, 'short_status'): # already done
            return
        self.starred = 0
        '''TODO: change the way it's stored and passed on.

        display will not be everything in a pile, but seperate:

        [###==+++|#==+|##=++++++]
        Sp a req w/ 3 children, each of whom have courses

        self.full_status will look like:
        {
            'count': 4,
            '
        '''
        self.child_status = {
            'completed': [],
            'registered': [],
            'organized': [],
            'unorganized': [],
            'notdone': [],
            'starred': [],
        }
        self.full_status = {
            'completed': [],
            'registered': [],
            'organized': [],
            'unorganized': [],
            'notdone': [],
            'starred': [],
        }
        self.total = 0
        order = ('completed', 'registered',
                'organized', 'unorganized', 'notdone')
        self.short_status = 'completed'
        for child in self.get_children():
            child = child.get_real()
            child.evaluate(user)
            if isinstance(child, Course):
                self.total += 1
                self.full_status[child.status].append(child)
                self.child_status[child.status].append(child)
                if child.starred:
                    self.full_status['starred'].append(child)
                    self.child_status['starred'].append(child)
                # if order.index(child.status) > order.index(self.short_status):
                    # self.short_status = child.status
            elif isinstance(child, Requirement):
                self.total += child.total
                self.child_status[child.short_status].append(child)
                for k in self.full_status:
                    # self.full_status[k] += child.full_status[k]
                    self.full_status[k].append(child)
                # if order.index(child.short_status) > order.index(self.short_status):
                    # self.short_status = child.short_status
        total = 0
        self.short_status = 'notdone'
        self.stat_percentages = {}
        for status in order:
            total += len(self.child_status[status])
            self.stat_percentages[status] = total / float(self.count)
            if total >= self.count:
                self.short_status = status
                break
        # TODO: logic for HOURS

    _cached_loadingbar = None
    def make_loadingbar(self):
        '''Returns the HTML of a loading bar. For a 'fulfil 5 of 5 courses' that looks like
        <!-- we don't provide the outermost idv -->
        <div class="course reuired [status]" data-name="name"></div>
        <div class="course reuired [status]" data-name="name" data-?="""></div>
        <div class="course reuired [status]"></div>
        <div class="course reuired [status]"></div>
        '''
        if self._cached_loadingbar is not None:
            return self._cached_loadingbar
        order = ('completed', 'registered',
                'organized', 'unorganized', 'notdone')
        if self.children.all().count() == self.count:
            text = ''
            for status in order:
                for child in self.child_status[status]:
                    if isinstance(child, Course):
                        text += '<div class="course required %s" data-name="%s" data-id="%s"></div>\n' % (child.status, child.long_name, child.code())
                    else:
                        text += '<div class="requirement required %s" data-name="%s">%s</div>\n' % (child.short_status, child.title, child.make_loadingbar())
            self._cached_loadingbar = text
            return text
        else:
            total = 0
            text = ''
            for status in order:
                if total >= self.count:
                    break
                for child in self.child_status[status]:
                    if total >= self.count:
                        break
                    if isinstance(child, Course):
                        text += '<div class="course required %s" data-name="%s" data-id="%s"></div>\n' % (child.status, child.long_name, child.code())
                    else:
                        text += '<div class="requirement required %s" data-name="%s">%s</div>\n' % (child.short_status, child.title, child.make_loadingbar())
                    total += 1
            self._cached_loadingbar = text
            return text


        '''
        children = self.cache_children
        if len(children) == self.count: ## no troubles
            text = ''
            for child in children:
                child = child.get_real()
                if isinstance(child, Course):
                    text += '<div class="course required %s" data-name="%s"></div>\n' % (child.status, child.long_name)
                else:
                    text += '<div class="requirement required %s" data-name="%s">%s</div>\n' % (child.short_status, child.title, child.make_loadingbar())
            self._cached_loadingbar = text
            return text
            '''
        self._cached_loadingbar = ''
        return ''

    def is_satisfied(self, user):
        good = 0
        for child in self.get_children():
            if child.is_satisfied(user):
                good += 1
                if good >= self.min:
                    return True
        return False

class Program(ModelBase):
    title = models.CharField(max_length=200)
    pid = models.PositiveIntegerField()
    internal_id = models.PositiveIntegerField()
    children = models.ManyToManyField(RequirementChild)

    def __unicode__(self):
        return self.title

    def type(self):
        if self.pid == 31044:# TODO generalize
            return 'general'
        else:
            return 'major'

    cache_children = False
    def get_children(self):
        if not self.cache_children:
            self.cache_children = list(self.children.all())
        return self.cache_children

    _cached_loadingbar = None
    def make_loadingbar(self):
        '''Returns the HTML of a loading bar. For a 'fulfil 5 of 5 courses' that looks like
        <!-- we don't provide the outermost idv -->
        <div class="course reuired [status]" data-name="name"></div>
        <div class="course reuired [status]" data-name="name" data-?="""></div>
        <div class="course reuired [status]"></div>
        <div class="course reuired [status]"></div>
        '''
        if self._cached_loadingbar is not None:
            return self._cached_loadingbar
        order = ('completed', 'registered',
                'organized', 'unorganized', 'notdone')
        text = ''
        for status in order:
            for child in self.child_status[status]:
                if isinstance(child, Course):
                    text += '<div class="course required %s" data-name="%s"></div>\n' % (child.status, child.long_name)
                else:
                    text += '<div class="requirement required %s" data-name="%s">%s</div>\n' % (child.short_status, child.title, child.make_loadingbar())
        self._cached_loadingbar = text
        return text


    def evaluate(self, user):
        if hasattr(self, 'short_status'):
            return
        order = ('completed', 'registered',
                'organized', 'unorganized', 'notdone')
        self.child_status = {
            'completed': [],
            'registered': [],
            'organized': [],
            'unorganized': [],
            'notdone': [],
            'starred': [],
        }
        self.short_status = 'completed'
        for child in self.get_children():
            child = child.get_real()
            child.evaluate(user)
            self.child_status[child.short_status].append(child)
            if order.index(child.short_status) > order.index(self.short_status):
                self.short_status = child.short_status

TERM_CHOICES = make_long_choices(
    'Winter',
    'Spring',
    'Summer',
    'Fall',
    )

FLAGS = make_choices(
    'Completed',
    'Registered',
    'Planned',
    'Starred',
    )

FLAG_ORDER = [f[0] for f in FLAGS]

class Term(ModelBase):
    year = models.PositiveIntegerField()
    term = models.CharField(max_length=10, choices = TERM_CHOICES)
    termno = models.PositiveIntegerField()
    student = models.ForeignKey(User)
    ## in the future, disallow rearrangement of past terms
    past = models.BooleanField()

    @classmethod
    def byshort(cls, short):
        year, nice, tno = cls.unshorten(short)
        return cls.objects.get(year=year, termno=tno)

    TERMS = ['winter', 'spring', 'summer', 'fall']
    @classmethod
    def unshorten(cls, short):
        parts = short.split('-')
        return int(parts[0]), cls.TERMS[int(parts[1])], int(parts[1])

    @classmethod
    def shorten(cls, year, term):
        return '%d-%d' % (year, cls.TERMS.index(term.lower()))

    def ispast(self):
        return self.year < 2012 or (self.year == 2012 and self.termno < 3)

    def short(self):
        return '%d-%d' % (self.year, self.termno)

    def long_name(self):
        return '%s %d' % (self.term.title(), self.year)

    def courses(self):
        result = []
        for flag in self.courseflag_set.exclude(flag='s'):
            flag.course.status_flag(flag)
            if flag.course not in result:
                result.append(flag.course)
        return result

    class Meta:
        ordering = ['year', 'termno']

class CourseFlag(ModelBase):
    term = models.ForeignKey(Term, blank=True, null=True)
    course = models.ForeignKey(Course)
    student = models.ForeignKey(User)
    flag = models.CharField(max_length=10, choices = FLAGS)
    grade = models.CharField(max_length=5, blank=True, null=True)
    comments = models.TextField()

    def __unicode__(self):
        return 'Flag for %s:%s with %s: %s' % (self.course.department.code, self.course.num, self.student.username, self.flag)


# Create your models here.
