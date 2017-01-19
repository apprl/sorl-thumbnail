#!/usr/bin/env bash
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

pip install -r etc/requirements.dev.pip &

project_path=./devops/docker/apprl

docker-compose -f $project_path/docker-compose.yml down
docker-compose -f $project_path/docker-compose.yml up --force-recreate -d

if [[ $(nc -z -w5 localhost 5432) -ne 0 ]]
then
    echo "Could not connect to database"
    exit 1
fi


echo "Get development database backup from s3"
aws s3 sync s3://apprl-vagrant/dev_db_backups/ devops/dev_db_backups/.

echo "Restore database apprl_db_backup.sql"
until createdb apparel -hlocalhost -Upostgres
do
    echo "Retry create db in two seconds, postgres probably still starting up"
    sleep 2
done

pg_restore --verbose --no-acl --no-owner -h localhost -U postgres -d apparel ./devops/dev_db_backups/latest_apprl_dev_backup.sql

echo "Migrate database"
./manage.py migrate

echo "Delete all product data to later repopulate it"
echo 'from apparelrow.dashboard.models import UserEarning; UserEarning.objects.all().delete()' | ./manage.py shell
echo 'from apparelrow.apparel.models import Product; Product.objects.all().delete()' | ./manage.py shell

echo "Import data from shirtonomy"
cd spiderpig
scrapy crawl shirtonomy
cd -

echo "Reindex data to make sure all is up-to-date"
./manage.py rebuild_index --clean --model=product
# if rebuild index craches on images try running  ./manage.py thumbnail clear first

# echo "Run tests"
# ./manage.py test

# If pillow for some reason does not work try this.
# brew install libjpeg && pip install --no-cache-dir -I pillow==1.7.8
