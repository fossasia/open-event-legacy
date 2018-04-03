#!/bin/bash
cp .env.sample .env
postgres -D /usr/local/pgsql/data >logfile 2>&1 &
service postgresql restart
python create_db.py
# download and run redis
if [ ! -d redis-3.2.1/src ]; then
    wget http://download.redis.io/releases/redis-3.2.1.tar.gz
    tar xzf redis-3.2.1.tar.gz
    rm redis-3.2.1.tar.gz
    cd redis-3.2.1
    make
fi

redis-3.2.1/src/redis-server &
# run worker
celery worker -A app.celery &
# run app
python manage.py runserver -h 0.0.0.0 -p 5000
