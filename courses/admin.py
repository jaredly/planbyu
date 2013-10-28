#!/usr/bin/env python

from django.contrib import admin
from models import Department, Course, Program, Requirement, CourseFlag

admin.site.register(Department)
admin.site.register(Course)
admin.site.register(Program)
admin.site.register(Requirement)
admin.site.register(CourseFlag)

# vim: et sw=4 sts=4
