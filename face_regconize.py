import time
import mysql.connector
from datetime import date
from datetime import timedelta
from datetime import datetime
import json
import numpy as np
from annoy import AnnoyIndex
import pyrealsense2 as rs
import cv2
import face_recognition
import math
from collections import Counter
import os
from kafka import KafkaProducer


def connection():
    mydb = mysql.connector.connect(
        host = "localhost",
        user = "root",
        password = "12345",
        database = "testdb"
    )
    return mydb

ten = []
attendance_path = 'attendance_img'
today = date.today()
previous_day = today - timedelta(days=1)

topic_name = "streaming"
p = KafkaProducer(
    bootstrap_servers=["localhost:9092"],
    max_request_size=9000000,
    api_version=(0, 10, 2)
)

def load_data_mysql():
    global ten
    ten = []
    i = 0
    database = connection()
    cursor = database.cursor()
    cursor.execute("SELECT name, username, role, vectorencode0, vectorencode1, vectorencode2, vectorencode3, vectorencode4 FROM users")
    result = cursor.fetchall()
    for item in result:
        if item[2] == "display":
            pass
        else:
            vector_encode_lst = [item[3], item[4], item[5], item[6], item[7]]
            ten.append(f"{item[0]}-{item[1]}")
            for vector_mysql in vector_encode_lst:
                # print(type(vector_mysql))
                data = json.loads(vector_mysql)
                # print(type(data))
                vector = np.array(data)
                t.add_item(i, vector)
                i += 1
    t.build(100)
    t.save("train/index_vector.ann")
    database.close()
    t.load("train/index_vector.ann")
    print(ten)
    print("Thanh cong")

def face_recognize():

    while True:
        frame = pipe.wait_for_frames()
        aligned_frames = align.process(frame)
        depth_frame = aligned_frames.get_depth_frame()
        color_frame = aligned_frames.get_color_frame()

        color_intrin = color_frame.profile.as_video_stream_profile().intrinsics
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())
        color_image = cv2.flip(color_image, 1)
        frameS = cv2.resize(color_image, (0, 0), fx=0.2, fy=0.2)


        time_record = datetime.now()
        time_record = time_record.strftime('%Y-%m-%d %H:%M:%S')
        database = connection()
        cursor = database.cursor()
        cursor.execute("SELECT * FROM history WHERE time BETWEEN '{}' AND '{}' AND checkupdate = 'no' AND (description = 'account register' OR description = 'update images' OR description = 'delete account')".format(previous_day, time_record))
        result = cursor.fetchall()
        database.close()
        if len(result) == 0:
            pass
        else:
            load_data_mysql()
            database = connection()
            cursor = database.cursor()
            cursor.execute("UPDATE history SET checkupdate = 'yes' WHERE checkupdate = 'no' AND (time BETWEEN '{}' AND '{}')".format(previous_day, time_record))
            database.commit()
            database.close()

        face_locations = face_recognition.face_locations(frameS)
        face_encodes = face_recognition.face_encodings(frameS)
        face_landmarks = face_recognition.face_landmarks(frameS)

        for face_encode, face_location, face_landmark in zip(face_encodes, face_locations, face_landmarks):
            known_face_encoding = []
            predict_name = []
            real_fake = ""

            y1, x2, y2, x1 = face_location
            y1, x2, y2, x1 = y1 * 5, x2 * 5, y2 * 5, x1 * 5

            x_nose_top = face_landmark["nose_bridge"][3][0] * 5
            y_nose_top = face_landmark["nose_bridge"][3][1] * 5

            depth = depth_frame.get_distance(abs(x_nose_top), abs(y_nose_top))
            dx, dy, dz = rs.rs2_deproject_pixel_to_point(color_intrin, [x_nose_top, y_nose_top], depth)
            distance = math.sqrt((dx) ** 2 + (dy) ** 2 + (dz) ** 2)

            if distance >= 0.25:
                matches = t.get_nns_by_vector(face_encode, 5)
                for i in matches:
                    known_face_encoding.append(t.get_item_vector(i))
                compare_faces = face_recognition.compare_faces(known_face_encoding, face_encode)
                # print(matches)
                if compare_faces.count(True) == 5:
                    for i in matches:
                        idx = int(math.floor(i/5))
                        predict_name.append(ten[idx])
                    # print(predict_name)
                    most_occur = Counter(predict_name)
                    most_occur = most_occur.most_common(1)[0][0]
                    if predict_name.count(most_occur) >= len(predict_name)-1:
                        name = most_occur
                    else:
                        name = "unknown"
                else:
                    name = "unknown"

                depth_image_c = depth_image[y1:y2, x1:x2]
                scale = (depth_image_c.max() - depth_image_c.min())
                print(scale)
                color_image_copy = color_image.copy()
                if scale < 1500:
                    real_fake = "fake"
                    cv2.putText(color_image, "Fake", (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    color_image = cv2.rectangle(color_image, (x1, y1), (x2, y2), (0, 0, 255), 2)
                else:
                    real_fake = "real"
                    color_image = cv2.rectangle(color_image, (x1, y1), (x2, y2), (0, 255, 0), 2)

                if name != "unknown":
                    now = datetime.now()
                    day_time = now.strftime('%Y-%m-%d %H-%M')
                    day_time_mysql = now.strftime('%Y-%m-%d %H:%M:%S')
                    day_time_with_sec = day_time_mysql.replace(" ", "_")
                    day_time_with_sec = day_time_with_sec.replace(":", "-")
                    day = day_time.split()[0]
                    times = day_time.split()[1]
                    if not os.path.isdir(attendance_path + "/" + f"{day}_{times}"):
                        os.mkdir(attendance_path + "/" + f"{day}_{times}")
                        os.mkdir(attendance_path + "/" + f"{day}_{times}" + "/" + "real")
                        os.mkdir(attendance_path + "/" + f"{day}_{times}" + "/" + "fake")
                    database = connection()
                    cursor = database.cursor()
                    cursor.execute('SELECT * FROM attendance WHERE username = %s AND day_time = %s AND real_fake = %s', (name.split("-")[1], day_time_mysql, real_fake))
                    is_exist = cursor.fetchone()
                    # print(is_exist)
                    if not is_exist:
                        file_path = attendance_path + "/" + f"{day}_{times}"
                        cursor.execute('INSERT INTO attendance VALUES (%s, %s, %s, %s, %s)', (name.split("-")[0], name.split("-")[1], day_time_mysql, file_path, real_fake))
                        database.commit()
                        cv2.imwrite(attendance_path + "/" + f"{day}_{times}" + "/" + f"{real_fake}" + "/" + f"{name.split('-')[0]}_{name.split('-')[1]}_{day_time_with_sec}" + ".jpg", color_image_copy)
                    database.close()


                cv2.putText(color_image, name, (x1, y2+35), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)

            else:
                cv2.putText(color_image, "Minimum distance is 25 cm", (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        ret, buffer = cv2.imencode('.jpg', color_image)
        color_image = buffer.tobytes()
        p.send(topic_name, color_image)
        p.flush()
        print("Da gui")
        time.sleep(0.1)

if __name__ == '__main__':
    t = AnnoyIndex(128, "euclidean")
    pipe = rs.pipeline()
    cfg = rs.config()
    cfg.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    cfg.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    pipe.start(cfg)
    align_to = rs.stream.color
    align = rs.align(align_to)
    load_data_mysql()
    face_recognize()