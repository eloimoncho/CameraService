# Camera service
## Introduction
The camera service is an on-board module that provides images to the rest of modules of the ecosystem, as required.
Dashboard or mobile applications will requiere the camera service to provide a single picture or to stard/stop a video stream.

## Installations
In order to run and contribute you must install Python 3.7. We recomend to use PyCharm as IDE for developments. In addition, you must install the broker Mosquitto. The internal broker will be always run in localhome, port 1884, in your laptop when working in simulation mode. You must edit the configuration file (_mosquitto.conf_) with the following lines: 

![image](https://github.com/eloimoncho/CameraService/assets/91852608/539db4d5-b37d-4474-bfef-b3aa0a187ee6)

And then run the file with the command: _mosquitto -v -c mosquitto.conf_

In order to contribute you must follow the contribution protocol described in the main repo of the Drone Engineering Ecosystem.
[![DroneEngineeringEcosystem Badge](https://img.shields.io/badge/DEE-MainRepo-brightgreen.svg)](https://github.com/dronsEETAC/DroneEngineeringEcosystemDEE)


## Commands
In order to send a command to the camera service, a module must publish a message in the external (or internal) broker. The topic of the message must be in the form:
```
"XXX/cameraService/YYY"
```
where XXX is the name of the module requiring the service and YYY is the name of the service that is required. Some of the commands may require additional data that must be include in the payload of the message to be published.
In some cases, after completing the service requiered the camera service publish a message as an answer. The topic of the answer has the format:
```
"cameraService/XXX/ZZZ"
```
where XXX is the name of the module requiring the service and ZZZ is the answer. The message can include data in the message payload.

The table bellow indicates all the commands that are accepted by the canera service in the current version.

Command | Description | Payload | Answer | Answer payload
--- | --- | --- | --- |---
*takePicture* | provides a picture | No | *picture* | Yes (see Note 1)
*startVideoStream* | starts sending pictures every 0.2 seconds | No | *picture* |Yes (see Note 1)
*stopVideoStream* | stop sending pictures | No | No | No

Note 1
Pictures are encoded in base64, as shown here:
```
  ret, frame = cap.read()
  if ret:
      _, image_buffer = cv.imencode(".jpg", frame)
      jpg_as_text = base64.b64encode(image_buffer)
      client.publish(topic_to_publish, jpg_as_text)
```
