#!/bin/bash

if [[ $SLACK_NOTIFICATIONS == "yes" ]]; then
    curl -X POST -H 'Content-type: application/json' --data '{"text":"Artifact event recieved, downloading artifact"}' $SLACK_WEBHOOK_URL
fi

ADMIN=$TIMESKETCH_USER
PW=$TIMESKETCH_PW
ZIP=$(python3 /opt/lcvr-to-timesketch/python/get_artifact.py $OID $SID $PAYLOAD_ID)
PARENT_DATA_DIR="/opt/timesketch/upload"

if [[ $SLACK_NOTIFICATIONS == "yes" ]]; then
    curl -X POST -H 'Content-type: application/json' --data '{"text":"Artifact downloaded..."}' $SLACK_WEBHOOK_URL
fi

if [[ $ZIP == *".zip.gz"* ]]; then
    # Get system name and params
    SYSTEM=${ZIP%.zip.gz}
    HOSTNAME=$(echo $SYSTEM|cut -d"_" -f 1)
    OID=$(echo $SYSTEM|cut -d"_" -f 2)
    FILENAME=$(echo $SYSTEM|cut -d"_" -f 3)

    # Gunzip
    echo A | gunzip $PARENT_DATA_DIR/$ZIP

    # Unzip
    echo A | unzip $PARENT_DATA_DIR/$SYSTEM.zip -d $PARENT_DATA_DIR/$SYSTEM
elif [[ $ZIP == *".zip"* ]]; then
    # Get system name and params
    SYSTEM=${ZIP%.*}
    HOSTNAME=$(echo $SYSTEM|cut -d"_" -f 1)
    OID=$(echo $SYSTEM|cut -d"_" -f 2)
    FILENAME=$(echo $SYSTEM|cut -d"_" -f 3)

    # Unzip
    echo A | unzip $PARENT_DATA_DIR/$ZIP -d $PARENT_DATA_DIR/$SYSTEM
fi

if [ -d $PARENT_DATA_DIR/$SYSTEM/uploads ]; then

    if [[ $SLACK_NOTIFICATIONS == "yes" ]]; then
    curl -X POST -H 'Content-type: application/json' --data '{"text":"Triage artifact unzipped, cleaning up files"}' $SLACK_WEBHOOK_URL
    fi

    # Remove collection data from subdir
    mv $PARENT_DATA_DIR/$SYSTEM/uploads/* $PARENT_DATA_DIR/$SYSTEM/

    # Delete unnecessary collection data
    rm -r $PARENT_DATA_DIR/$SYSTEM/results $PARENT_DATA_DIR/$SYSTEM/uploads.json* $PARENT_DATA_DIR/$SYSTEM/uploads $PARENT_DATA_DIR/$SYSTEM/log* $PARENT_DATA_DIR/$SYSTEM/collection* $PARENT_DATA_DIR/$SYSTEM/requests.json

    if [[ $SLACK_NOTIFICATIONS == "yes" ]]; then
    curl -X POST -H 'Content-type: application/json' --data '{"text":"Triage files organized, generating plaso file"}' $SLACK_WEBHOOK_URL
    fi

    # Run log2timeline and generate Plaso file
    docker exec -i timesketch-worker /bin/bash -c "log2timeline.py --status_view window --storage_file /usr/share/timesketch/upload/plaso/$SYSTEM.plaso /usr/share/timesketch/upload/$SYSTEM"

    # Wait for file to become available
    sleep 40

    # Get ID of sketch if it exists, otherwise create new sketch with OID
    SKETCHES=`docker exec -i timesketch-web tsctl list-sketches`
    while IFS= read -r line; do
        name=`echo $line|cut -f 2 -d " "`
        id=`echo $line|cut -f 1 -d " "`
        if [[ "$name" == "$OID" ]]; then
                SKETCH_ID=$id
        else
                SKETCH_ID="none"
        fi
    done <<< "$SKETCHES"

    if [[ $SLACK_NOTIFICATIONS == "yes" ]]; then
    curl -X POST -H 'Content-type: application/json' --data '{"text":"Plaso file generated, importing into Timesketch--progress will be visible in the Timesketch GUI"}' $SLACK_WEBHOOK_URL
    fi

    # Run timesketch_importer to import Plaso data into Timesketch
    if [[ "$SKETCH_ID" == "none" ]]; then
        docker exec -i timesketch-worker /bin/bash -c "timesketch_importer -u $ADMIN  -p $PW --host http://timesketch-web:5000 --timeline_name $HOSTNAME-$FILENAME --sketch_name $OID /usr/share/timesketch/upload/plaso/$SYSTEM.plaso"

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
        docker exec timesketch-worker /bin/bash -c "timesketch_importer -u $ADMIN -p $PW --host http://timesketch-web:5000 --timeline_name $HOSTNAME-$FILENAME --sketch_id $SKETCH_ID /usr/share/timesketch/upload/plaso/$SYSTEM.plaso"
    fi

    if [[ $SLACK_NOTIFICATIONS == "yes" ]]; then
    curl -X POST -H 'Content-type: application/json' --data '{"text":"Finished importing plaso file into Timesketch - http://'$WEBHOOK_IP'/sketch/'$SKETCH_ID'/explore"}' $SLACK_WEBHOOK_URL
    fi

else 

    echo "base64 contents of collection downloaded to $PARENT_DATA_DIR/$SYSTEM"

    if [[ $SLACK_NOTIFICATIONS == "yes" ]]; then
    curl -X POST -H 'Content-type: application/json' --data '{"text":"Not a triage artifact - payload converted and saved to '$PARENT_DATA_DIR/$SYSTEM'"}' $SLACK_WEBHOOK_URL
    fi

fi