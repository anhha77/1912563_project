# Face recognition web app using Jetson Nano

## Languages and tool for this project

<div style="display: flex; flex-direction: row; justify-content: flex-start; gap: 10px;"><a href="https://www.w3schools.com/css/" target="_blank" rel="noreferrer"> <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/css3/css3-original-wordmark.svg" alt="css3" width="40" height="40"/> </a><a href="https://www.w3.org/html/" target="_blank" rel="noreferrer"> <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/html5/html5-original-wordmark.svg" alt="html5" width="40" height="40"/> </a><a href="https://developer.mozilla.org/en-US/docs/Web/JavaScript" target="_blank" rel="noreferrer"> <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/javascript/javascript-original.svg" alt="javascript" width="40" height="40"/> </a><a href="https://www.python.org/" target="_blank" rel="noreferrer"><img src="https://s3.dualstack.us-east-2.amazonaws.com/pythondotorg-assets/media/files/python-logo-only.svg" alt="python" width="40" height="40"/></a><a href="https://flask.palletsprojects.com/en/3.0.x/" target="_blank" rel="noreferrer"><img src="./result/Flask.png" alt="flask" width="40" height="40"/></a><a href="https://docs.celeryq.dev/en/stable/getting-started/introduction.html" target="_blank" rel="noreferrer"><img src="https://raw.githubusercontent.com/celery/celery/master/docs/images/celery_512.png" alt="celery" width="40" height="40"/></a><a href="https://www.mysql.com/"><img src="./result/MySQL.png" alt="mysql" width="40" height="40"/></a><a><img src="./result/Redis.png" alt="redis" width="40" height="40"/></a><a><img src="./result/Apache Kafka.png" alt="apache kafka" width="40" height="40"/></a></div>

## Hardward for this project

![](./result/JetsonNano-DevKit_Front-Top_Right_trimmed.jpg)

![](./result/Intel-RealSense-D435i.jpg)

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

In addtion to features like user, admin can monitor attendance activities and search user.

- Search user

![](./result/Screenshot%202023-08-21%20112655.png "UI for search user")

There are two ways to search user by name or by time range:

- Search by name

![](./result/Screenshot%202023-08-21%20112855.png "Seach user by name (1)")

![](./result/Screenshot%202023-08-21%20112916.png "Search user by name (2)")

- Search by time range

![](./result/Screenshot%202023-08-21%20113500.png "Search user by time range")

- Delete user from databse

![](./result/Screenshot%202023-08-21%20113159.png "Delete user from database (1)")

![](./result/Screenshot%202023-08-21%20113412.png "Delete user from database (2)")

- Sign up

To sign up user enter name, username and password and upload 5 portrait images.

![](./result/Screenshot%202023-09-19%20215526.png "UI for sign up")

![](./result/Screenshot%202023-08-21%20113827.png "User that doesnt in database")

![](./result/Screenshot%202023-09-19%20223242.png "Sign up")

![](./result/Screenshot%202023-08-21%20114111.png "Sign up completed")

## Disadvantages when using Jetson Nano as server

We have to use swap file to deal with the limit in memory of Jetson and it affect to the speed of system.

![](./result/Screenshot%20from%202023-08-21%2011-38-40.png "Jetson memory")

## References

- J. Deng, J. Guo, J. Yang, N. Xue, I. Kotsia and Z. Stefanos, "ArcFace: Additive Angular
  Margin Loss for Deep".

- W. Liu, Y. Wen, Z. Yu, M. Li, B. Raj and L. Song, "SphereFace: Deep Hypersphere
  Embedding for Face Recognition".

- F. Schroff, D. Kalenichenko and J. Philbin, "FaceNet: A Unified Embedding for Face
  Recognition and Clustering".
