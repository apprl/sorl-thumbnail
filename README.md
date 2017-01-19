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

### System requirements OS X ###

First of all you need to have brew installed see http://brew.sh
You also need docker to run the services used by the dev_reset.sh script.
You can install docker via brew cask ```brew cask install docker```, remember to start it, it will not start automatically after install.

Important note! Before running dev_reset.sh make sure postgres, memcached, redis are NOT running on your local machine.
As we are using docker for all services your locally installed services will use the same ports (if you are using the standard ports).

Install following libs and services

```
# Installes nvm for Node, a "virtualenv" for Node
brew install nvm
nvm install 5
nvm use 5
# Install less, used by apprl
npm install -g less
# Install virtualenvwrapper
sudo pip install pbr
sudo pip install --no-deps stevedore
sudo pip install --no-deps virtualenvwrapper
# Install clients for all services. The actual service should be run in docker.
brew install redis
brew install postgres
brew install memcached
brew install libmemcached
brew install lessc
brew install nvm
brew install libjpeg
brew cask install java
# You will need awscli to run the dev_reset.sh as the development database is located on s3.
brew install awscli
```

After installing awscli run ```awscli configure```

Now you should be all set to continue with the setup.

### Running dev_reset.sh ###

Check out the project from github (ask some one as you will need permissions)
Create an virtual environment using virtual wrapper.
Copy the apparel_db_backup.sql to the apprl root directory.

run ```./dev_reset.sh```
This command will create docker containers, run pip install and restore the apparel_db_backup.sql and index data from shirtonomy.
run ```./manage.py test```
If it starts you don't have to wait until it finishes you can start the web server while the tests are running.
run ```./manage.py runserver```
Visit http://localhost:8000, enjoy!

### Some useful docker commands ###

To list all running and stoped containers
```
docker ps -a
```

To show memory and process usage of running containers
```
docker stats $(docker ps --format={{.Names}})
```

To start all containers started from the docker-compose.yml file
```
docker-compose -f ./docker/apprl/docker-compose.yml start
```

To stop all containers started from the docker-compose.yml file
```
docker-compose -f ./docker/apprl/docker-compose.yml stop
```

To stop all running containers with apprl in the name
```
docker stop $(docker ps | grep "apprl" | awk '{print $1}')
```

To remove all running containers with apprl in the name
```
docker rm -f $(docker ps -a | grep "apprl" | awk '{print $1}')
```

To remove all docker images with apprl in the name
```
docker rmi -f $(docker images -a | grep "apprl" | awk '{print $1}')
```

## Should the following stuff still be here? ##

### System requirements Ubuntu ###
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
