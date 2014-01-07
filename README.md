# APPRL

## Setup production servers ##

Add a user called deploy and add it to sudoers. Install ufw and setup correct
rules for webservers, databases and solr.

Make sure that that the fabric environments `production_data` and `production_web`
is correct and the run the following fabric commands:

```
fab production_data setup_data_server
fab production_web setup
```

Remember to setup `/etc/ssl/apprl.com.crt` and `/etc/ssl/apprl.com.key` before
running setup on a web server. The SSL certifacte and the private key is not
stored in the git repo.


## Setup importer servers ##

Add a user called deploy and add it to sudoers. Install ufw and setup correct
rules for scrapyd.

Make sure that that the fabric environment `production_import` is correct and
the run the following fabric commands:

```
fab production_importer setup_importer_server
fab production_importer deploy_importer_server
```

## Restore WAL-E backup (untested) ##
```
export ENVDIR=/etc/wal-e.d/env
export PGDATA=/var/lib/postgresql/9.1/main
export LATEST=`envdir $ENVDIR wal-e backup-list | tail -1 | awk '{ print $3 }'`

/etc/init.d/postgresql stop

rm -rf $PGDATA
envdir $ENVDIR wal-e backup-fetch $PGDATA LATEST
envdir $ENVDIR wal-e wal-fetch $LATEST $PGDATA/pg_xlog/$LATEST
chmod 0700 $PGDATA
chown -R postgres:postgres $PGDATA

/etc/init.d/postgresql start
```

## Setup development environment ##

TODO: setup for OS X / PyCharm

### system requirements ###
```
aptitude install python-software-properties
add-apt-repository ppa:chris-lea/node.js
aptitude install git python-virtualenv python-dev libxml2-dev libxslt1-dev libyaml-dev libjpeg-dev libtiff-dev openjdk-6-jre-headless nodejs
aptitude install postgresql libpq-dev # required for psycopg2 python requirement in later step
npm install -g less
```

### setup virtualenv ###
```
virtualenv apparelrow
cd apparelrow
source bin/activate
```

### clone repository and install requirements ###
```
git clone git@github.com:martinlanden/apprl.git apparelrow
pip install -r apparelrow/etc/requirements.pip # ... fika ...
```

### settings and create folders ###
```
cp apparelrow/apparelrow/development.py.default apparelrow/apparelrow/settings.py
mkdir -p var/logs
```
Update settings.py to match your local environment.

### Set up solr ###
```
# Update paths in fabric file localhost target and run (debian/ubuntu only)
pip install fabric fabtools jinja2
mkdir {solr-path}
fab localhost install_solr start_solr deploy_solr

# Or install it manually for your system and make sure that you copy the files in deploy_solr fabric command
```

### Set up database ###
```
cd apparelrow
./manage.py syncdb
./manage.py migrate
./manage.py createsuperuser
./manage.py loaddata apparel/fixtures/*
./manage.py loaddata importer/fixtures/*
```

Now you can start django, either with the django-admin.py in bin, or the regular manage.py

## Directory Structure ##
```
.               This directory
./bin           General scripts, such as the FCGI daemon controller
./apparelrow    Django application root directory
./advertiser    Advertiser module
./theimp        The importer module
./spiderpig     Scrapy project for scraping feeds and pages
./etc           Non-Django related configuration files, such as webserver config
./docs          General documentation
```
