# APPRL

## Setup a production server ##

Add a user called deploy and add it to sudoers. Install ufw and setup correct
rules for webservers, databases and solr.

Make sure that that the fabric environments production_data and production_web
is correct and the run the following fabric commands:

```
fab production_data setup_data_server
fab production_web setup
```


## Setup development environment ##

### virtualenv ###
```
virtualenv-2.6 --no-site-packages apparelrow
cd apparelrow
source bin/activate
```

### pip ###
```
easy_install pip
pip install -r etc/requirements.pip # ... fika ...
```

### settings ###
```
cp etc/logging.conf.default etc/logging.conf
cp apparelrow/development.py.default apparelrow/development.py

mkdir -p var/logs
```

### build js ###
```
cd apparelrow
./manage.py synccompress
```

### Set up database ###
```
cd apparelrow
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
./conf          Non-Django related configuration files, such as webserver config
./docs          General documentation
```

### If rebuilding schema.xml ###
```
./manage.py build_solr_schema > schema.xml
Replace field type with name slong with:
    <fieldType name="slong" class="solr.TrieIntField" precisionStep="0" omitNorms="true" positionIncrementGap="0"/>
```

Field with name name should have type string not text
