# Face recognition web app using Jetson Nano

## Setup for face recognition system

We must install redis-server and kafka-server for Jetson Nano.

### Run kafka-server

- Open terminal and cd to kafka.

- Run zookeeper-server by command: bin/zookeeper-server-start.sh
  config/zookeeper.properties.

- Run kafka-server by command: bin/kakfa-server-start.sh config/server.properties.

### Run redis and celery

- rq worker.

- celery –A flask_server.celery worker –l info –P eventlet.

### Run face recognition program and server

- python3 flask_server.py.

- python3 face_recognize.py.

## Result

### Face recognition

![](./result/Screenshot%202023-08-21%20110944.png)

![](./result/Screenshot%202023-08-21%20111305.png)

![](./result/Screenshot%202023-08-21%20111359.png)

![](./result/Screenshot%202023-08-21%20111444.png)

### User

- View time attend

![](./result/Screenshot%202023-08-21%20111602.png "View time attend")

- User can update password or user images. For update images user upload 5 portrait images. When user click update system will return a notification that has task id of the task for user keep track.

![](./result/Screenshot%202023-08-21%20112023.png "UI for update images")

![](./result/Screenshot%202023-09-19%20201117.png "Notification")

![](./result/Screenshot%202023-09-19%20202043.png "Progress of task (1)")

![](./result/Screenshot%202023-09-19%20202316.png "Progress of task (2)")

- We can view the track by click the button next to Update button. When task is not done the status is a clock icon, the result and time complete are not available.

- When task done the status is a green tick, result and time are available.

### Admin
