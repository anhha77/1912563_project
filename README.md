# Face recognition web app using Jetson Nano

## Setup for face recognition system

We must install redis-server and kafka-server for Jetson Nano.

---

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

---

### Face recognition

![](./result/Screenshot%202023-08-21%20110944.png)
