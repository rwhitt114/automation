# automation
automation scripts
Scale_control.py is a control script that will scaleout a newly created VS to all SE's. 
  1. Log into the controller UI
  2. Navigate to Operations > Alerts > Alert Config > Create
  3. Create an alert config with the following peramiters (leave everything else default):
    - Throttle alert: 0
    - Source: Event
    - Object: Virtual Service
    - Event Occurs: Config Create
    - Action: Create Action
      - Control script: Create Control Script
        - Upload file: scale_control.py
        -save
      -save
    -save
    
This script will log status and errors to /var/log/scale.log on the Avi controller.
