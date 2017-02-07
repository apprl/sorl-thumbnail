
COPY_INSTANCE=${1-prod-copy}

echo "This command will DELETE a prod copy instance: $COPY_INSTANCE"

read -p "Continue? (y/n) " -n 1 -r
echo    # move to new line
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    exit 1
fi

aws rds delete-db-instance --db-instance-identifier $COPY_INSTANCE --skip-final-snapshot > /dev/null 2>&1
