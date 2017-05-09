#!/bin/bash

COPY_INSTANCE=${1-prod-copy}

green=$'\e[1;32m'
red=$'\e[1;31m'
end=$'\e[0m'

function echo_green {
    printf "%s\n" "${green}$1${end}"
}

function wait-for-status {
    instance=$1
    target_status=$2
    status=unknown
    while [[ "$status" != "$target_status" ]]; do
        status=$(aws rds describe-db-instances --db-instance-identifier=$instance | jq -r '.DBInstances[0].DBInstanceStatus')
        printf '.'
        sleep 5
    done
    echo ''
}

LATEST_PROD_SNAPSHOT=$(aws rds describe-db-snapshots --db-instance-identifier=appareldbinstance | jq -r '.DBSnapshots[-1].DBSnapshotIdentifier')

echo "This command will create a prod copy instance: $COPY_INSTANCE"
echo "and create a new based on new prod snapshot: $LATEST_PROD_SNAPSHOT"

read -p "Continue? (y/n) " -n 1 -r
echo    # move to new line
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    exit 1
fi


echo_green "Creating $COPY_INSTANCE from latest prod snapshot: $LATEST_PROD_SNAPSHOT"

aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier $COPY_INSTANCE \
    --db-snapshot-identifier $LATEST_PROD_SNAPSHOT \
    --db-instance-class db.t2.small \
    --db-subnet-group-name apprldbgroup \

echo_green "Waiting for new DB instance to be available"
wait-for-status $COPY_INSTANCE available
echo_green "New instance is available"

echo_green "Modifying instance"
aws rds modify-db-instance \
    --db-instance-identifier $COPY_INSTANCE \
    --backup-retention-period 0 \
    --master-user-password Frikyrk4 \
    --vpc-security-group-ids sg-0a64fd6c \
    --apply-immediately

wait-for-status $COPY_INSTANCE available

endpoint=$(aws rds describe-db-instances --db-instance-identifier=$instance | jq -r '.DBInstances[0].Endpoint.Address')
echo_green "New instance is ready for use: $endpoint"
echo_green "Remember, you have to been on our AWS VPN & cleanup when you're done - : $endpoint"
