#!/bin/bash

if [[ $SLACK_NOTIFICATIONS == "yes" ]]; then
    curl -X POST -H 'Content-type: application/json' --data '{"text":"Artifact event recieved, downloading artifact"}' $SLACK_WEBHOOK_URL
fi

ADMIN=$TIMESKETCH_USER
PW=$TIMESKETCH_PW
FILE=$(python3 /opt/lcvr-to-timesketch/python/get_artifact.py $OID "" $PAYLOAD_ID "hayabusa")
PARENT_DATA_DIR="/opt/timesketch/upload"

if [[ $SLACK_NOTIFICATIONS == "yes" ]]; then
    curl -X POST -H 'Content-type: application/json' --data '{"text":"Artifact downloaded..."}' $SLACK_WEBHOOK_URL
fi

# If Hayabusa file has been downloaded, prepare for ingestion
if [ -f $PARENT_DATA_DIR/$FILE ]; then

    # Get ID of sketch if it exists, otherwise create new sketch with OID
    SKETCHES=`docker exec -i timesketch-web tsctl list-sketches`
    SKETCH_ID="none"
    while IFS= read -r line; do
        name=`echo $line|cut -f 2 -d " "`
        id=`echo $line|cut -f 1 -d " "`
        if [[ "$name" == "$OID" ]]; then
                SKETCH_ID=$id
        fi
    done <<< "$SKETCHES"

    if [[ $SLACK_NOTIFICATIONS == "yes" ]]; then
    curl -X POST -H 'Content-type: application/json' --data '{"text":"Importing Hayabusa CSV into Timesketch--progress will be visible in the Timesketch GUI"}' $SLACK_WEBHOOK_URL
    fi

    # Run timesketch_importer to import Hayabusa data into Timesketch
    if [[ "$SKETCH_ID" == "none" ]]; then
        docker exec -i timesketch-worker /bin/bash -c "timesketch_importer -u $ADMIN  -p $PW --host http://timesketch-web:5000 --timeline_name $PAYLOAD_ID --sketch_name $OID /usr/share/timesketch/upload/$FILE"

        # Get new ID of sketch 
        SKETCHES=`docker exec -i timesketch-web tsctl list-sketches`
        while IFS= read -r line; do
            name=`echo $line|cut -f 2 -d " "`
            id=`echo $line|cut -f 1 -d " "`
            if [[ "$name" == "$OID" ]]; then
                    SKETCH_ID=$id
            fi
        done <<< "$SKETCHES"
    else
        docker exec timesketch-worker /bin/bash -c "timesketch_importer -u $ADMIN -p $PW --host http://timesketch-web:5000 --timeline_name $PAYLOAD_ID --sketch_id $SKETCH_ID /usr/share/timesketch/upload/$FILE"
    fi

    if [[ $SLACK_NOTIFICATIONS == "yes" ]]; then
    curl -X POST -H 'Content-type: application/json' --data '{"text":"Finished importing Hayabusa CSV into Timesketch - http://'$WEBHOOK_IP'/sketch/'$SKETCH_ID'/explore"}' $SLACK_WEBHOOK_URL
    fi

fi