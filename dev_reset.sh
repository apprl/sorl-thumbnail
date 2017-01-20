#! /bin/bash

green=$'\e[1;32m'
end=$'\e[0m'

function echo_green {
    printf "%s\n" "${green}$1${end}"
}

echo "This command will remove all data in all your running docker containers!"
echo "Docker containers will be recreated and data will be restored from apprl_db_backup.sql."
echo "The database will also be repopulated and reindexed."
echo "When done your developement environment should be ready to go."
echo "Run './manage.py runserver' and visit http://localhost:8000"

read -p "Continue? (y/n) " -n 1 -r
echo    # move to new line
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    exit 1
fi

echo_green "Setting up docker"

project_path=./devops/docker/apprl
docker-compose -f $project_path/docker-compose.yml down
docker-compose -f $project_path/docker-compose.yml up --force-recreate -d

if [[ $(nc -z -w5 localhost 5432) -ne 0 ]]
then
    echo "Could not connect to database"
    exit 1
fi


echo_green "Get development database backup from s3"
aws s3 sync s3://apprl-vagrant/dev_db_backups/ devops/dev_db_backups/.

echo_green "Creating database, we'll get errors until postgres is initialized"
until createdb apparel -hlocalhost -Upostgres
do
    sleep 1
done

# We have two database dumps:
# latest_small_dev_backup.sql
# latest_dev_backup.sql - same as small dump, but contains productstats, products etc.

echo_green "Restore database apprl_db_backup.sql"
pg_restore --clean --if-exists --verbose --no-acl --no-owner -h localhost -U postgres -d apparel ./devops/dev_db_backups/latest_small_dev_backup.sql


echo_green "Install requirements"
pip install -r etc/requirements.dev.pip &

echo_green "Migrate database"
./manage.py migrate

echo_green "Import data from shirtonomy"
cd spiderpig
scrapy crawl shirtonomy
cd -

echo_green "Reindex data to make sure all is up-to-date"
./manage.py rebuild_index --clean

# echo "Run tests"
# ./manage.py test

# If pillow for some reason does not work try this.
# brew install libjpeg && pip install --no-cache-dir -I pillow==1.7.8
