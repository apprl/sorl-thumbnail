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

### virtualenv ###
```
virtualenv apparelrow
cd apparelrow
source bin/activate
```

### requirements ###
```
pip install -r etc/requirements.pip # ... fika ...
```

### settings ###
```
cp apparelrow/development.py.default apparelrow/development.py

mkdir -p var/logs
```
Update settings to match your local environment.

### Set up database ###
```
./manage.py syncdb # Warning: do not create a superuser in this stage
./manage.py migrate profile
./manage.py migrate
./manage.py createsuperuser
```

### Set up search ###
```
touch solr/solr/conf/synonyms.txt
cd solr
java -jar start.jar
./manage.py rebuild_index
```

### Continue set up database ###
```
./manage.py loaddata apparel/fixtures/*
./manage.py loaddata importer/fixtures/*
```

Now you can start django, either with the django-admin.py in bin, or the regular manage.py

### Directory Structure ###
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

### If rebuilding schema.xml ###
```
Replace field type with name slong with:
    <fieldType name="slong" class="solr.TrieIntField" precisionStep="0" omitNorms="true" positionIncrementGap="0"/>
```

Field with name name should have type string not text
