from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

try:
    from _special import args as special
except ImportError:
    print 'Importerror getting _special.py. Did you forget to create it?'

from _get_program import BYUBrowser, parse_program, parse_classes

from profileme import profile

class Command(BaseCommand):
    # todo: make it logon and download the file itself.
    args = 'ProgramId username'

    def handle(self, *args, **options):
        if len(args)!=2:
            raise CommandError('takes 2 args: programId, username')
        user = None
        try:
            user = User.objects.get(username=args[1])
        except User.DoesNotExist:
            raise CommandError('user %s does not exist' % args[1])
        try:
            pid = int(args[0])
        except:
            raise CommandError('ProgramId must be an integer, not %s' % args[0])
        dotheprofiling(pid, user)

@profile('/aml/home/jared/load_program.prof')
def dotheprofiling(pid, user):
    b = BYUBrowser(*special)
    program = b.get_program(pid, True)
    if pid:
        program.save(user)
    else:
        for course in program:
            course.save(user, None, False)

# vim: et sw=4 sts=4
