#!/usr/bin/env sh
watch_static(){
    while inotifywait -r -e modify -e create -e delete ./localstatic; do
        ./manage.py collectstatic --noinput
    done
}

echo "Watching SCSS"
compass watch resources &
echo "Watching Localstatic"
watch_static &
echo "Starting Webserver"
./manage.py runserver_plus
