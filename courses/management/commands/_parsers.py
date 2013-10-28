import re

e = re.escape

get_pid = re.compile(
        e('<input type="hidden" id="programId" value="') +
        '(\d+)' + e('"/>'))

regexes = {
    'lt': e('<input type="hidden" name="lt" value="') + '([^"]+)' + e('"/>'),
    'action': e('<form id="credentials" action="') + '([^"]+)' + e('" method="post">'),
    'execution': e('<input type="hidden" name="execution" value="') + '([^"]+)' + e('"/>'),

    'program_title': e('<span class="status">Selected Program:') + '([^<]+)<',
    'program_code': e('<span class="status">Program Code: ') + '(\d+)</span>',
    # TODO: grep other programs listed dropdown
}

for k in regexes.keys():
    regexes[k] = re.compile(regexes[k])

class MetaParse:
    def __getattr__(self, name):
        return regexes[name].findall

parse = MetaParse()

# def parse(name, text):
    # return regexes[name].findall(text)


# vim: et sw=4 sts=4
