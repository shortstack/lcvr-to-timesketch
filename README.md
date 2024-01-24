# lcvr-to-timesketch
Pipeline to process LimaCharlie Velociraptor Triages in Timesketch

## Ubuntu Deployment Steps
* Deploy Docker - [Deployment Directions](https://docs.docker.com/engine/install/ubuntu/)
    ```bash
    sudo apt-get update
    sudo apt-get install ca-certificates curl gnupg -y
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y
    sudo apt-get install docker-compose -y
    ```

* Deploy Timesketch - [Deployment Directions](https://github.com/google/timesketch/blob/master/docs/guides/admin/install.md)
    ```bash
    cd /opt
    curl -s -O https://raw.githubusercontent.com/google/timesketch/master/contrib/deploy_timesketch.sh
    chmod 755 deploy_timesketch.sh
    sudo ./deploy_timesketch.sh # At the end, choose to "not start containers"
    ```
    ```bash
    cd timesketch
    sudo docker compose up -d
    sudo docker compose exec timesketch-web tsctl create-user admin
    ```
    > **Note**  
    > **I strongly recommend deploying Timesketch with HTTPS**--additional instructions are provided [here](https://github.com/google/timesketch/blob/master/docs/guides/admin/install.md#4-enable-tls-optional). For this proof of concept, we're using HTTP. Modify your configs to reflect HTTPS if you deploy for production use. 
* Copy files
    ```bash
    cd /opt
    git clone https://github.com/shortstack/lcvr-to-timesketch.git
    cd lcvr-to-timesketch
    ```
* Modify the environment variables in `systemd/webhook.service`
    * `TIMESKETCH_USER` - Timesketch admin username
    * `TIMESKETCH_PW` - Timesketch password
    * `LC_API_KEY` - LimaCharlie API Key
    * `LC_UID` - LimaCharlie User ID
    * `SLACK_WEBHOOK_URL` - Slack webhook URL. Leave blank if `SLACK_NOTIFICATIONS` is `no`
    * `SLACK_NOTIFICATIONS` - Change to `yes` if you wish to recieve progress notifications
    * `WEBHOOK_IP` - External IP address of the system the webhook is running on (same as Timesketch)
* Modify the variables in `limacharlie/output.yaml`
    * `WEBHOOK_IP` - External IP address of the system the webhook is running on  (same as Timesketch)
    * `WEBHOOK_PORT`- Port of the system the webhook is running on--the default for the webhook service is `9000`
* Configuration script:
    ```bash
    # Install webhook and unzip
    sudo apt install webhook unzip -y 

    # Install timesketch_importer
    sudo docker exec timesketch-worker bash -c "pip3 install timesketch-import-client"

    # Fix permissions
    chmod +x /opt/lcvr-to-timesketch/bash/run.sh

    # Make sure Plaso dir exists
    mkdir -p /opt/timesketch/upload/plaso

    # Configure webhook as a service
    sudo cp systemd/webhook.service /etc/systemd/system/webhook.service
    sudo systemctl enable webhook.service
    sudo systemctl start webhook.service
    ```
    > **Note**  
    > **I strongly recommend deploying your webhooks with HTTPS.** If you wish to deploy your webhook with HTTPS, additional instructions are provided [here](https://github.com/adnanh/webhook?tab=readme-ov-file#using-https). For this proof of concept, we're using HTTP. Modify your configs to reflect HTTPS if you deploy for production use. 
* Add the `artifacts-tailored` tailored output in LimaCharlie - `limacharlie/output.yaml` - ensure `WEBHOOK_IP` and `WEBHOOK_PORT` have been updated to reflect your external IP and port

    ![](<./screenshots/Screenshot 2024-01-19 at 3.42.00 PM.png>)
* Add the `artifacts-to-output` D&R rule in LimaCharlie - `limacharlie/rules.yaml`

    ![](<./screenshots/Screenshot 2024-01-19 at 3.41.26 PM.png>)
* Kick off `Windows.KapeFiles.Targets` artifact collection in the LimaCharlie Velociraptor extension. 
  * Argument options:
    * `EventLogs=Y` - quicker processing time for proof of concept
    * `KapeTriage=Y` - typically takes much longer 

  ![](<./screenshots/Screenshot 2024-01-22 at 2.57.34 PM.png>)
* You can watch the `Live Feed` for your `ext-velociraptor` adapter to see incoming activity -- you will see `velociraptor_collection` events come in when triage artifacts have completed and will soon be sent to your webhook output for processing

    ![](<./screenshots/Screenshot 2024-01-19 at 3.59.28 PM.png>)
* You can see the data being sent through your output by clicking `View Samples` on the outputs screen
    * This JSON is what is being sent to your webhook, and you can see what parts of it we are using in the `webhook/hooks.json` file

    ![](<./screenshots/Screenshot 2024-01-19 at 4.00.43 PM.png>)
* If there are any errors sending data to your webhook, you will see them under `Platform Logs` -> `Error`
* If you have Slack notifications enabled in the webhook service, you will get progress updates in Slack
* Plaso files tend to take a while to generate--once the plaso file has been generated, it will begin importing into Timesketch. You will be able to see the import progress in the Timesketch GUI.