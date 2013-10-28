Steps to install
----------------

unpack bootstrap into /localstatic/
put jquery.min.js into /localstatic/js/libs/
put classy_js.js into /localstatic/js/libs/
put jquery.qtip.min.js in there
and jquery-ui-custom...js ?

...

run ./manage.py syncdb

./manage.py loaddeps
./manage.py loadprogram [pid]
