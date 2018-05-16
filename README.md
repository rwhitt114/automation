# automation
automation scripts
Scaleout_control.py is a control script that will scaleout a newly created VS to all SE's. 
  1. Log into the controller UI
  2. Navigate to Operations > Alerts > Alert Config > Create
  3. Create an alert config with the following peramiters (leave everything else default):
    - Throttle alert: 0
    - Source: Event
    - Object: Virtual Service
    - Event Occurs: Config Create
    - Action: Create Action
      - Control script: Create Control Script
        - Upload file: scaleout_control.py
        -save
      -save
    -save
 status and error will be logged to /var/log/scale.log on the Avi controller.



scale.py is a script that can be manually run to scaleout or scalein virtualservices. By default, all VS's will be scaled out to all SE's. The --scalein flag will scalein all VS's 1 time. A single virtualservice can be specified for either scalein or scaleout with the -V, --virtualservice flag. The -P, --plan flag will an overview of what the script will do. 
(i.e)  The following command will scalein all virtualservices that are scaled out.
python scale.py -c mycontroller.avi.local -u admin -p password -v

This script can be run on the controller, from any directory, or it can be run remotely. If run remotely, you will need to install AviSDK on the controller, see https://github.com/avinetworks/sdk/blob/master/README.md

You can see all the options by running:  python scale.py -h 
