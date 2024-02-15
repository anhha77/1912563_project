import numpy as np
from flask import Flask, render_template, request, redirect, Response, session, send_file, make_response, jsonify
import mysql.connector
import json
from PIL import Image
import xlsxwriter
from io import BytesIO
import cv2
import base64
import io
import os
import bcrypt
import shutil
import face_recognition
import pickle
import sys
from pyngrok import ngrok
from time import mktime
from datetime import date
from datetime import timedelta
from datetime import datetime
from celery import Celery
from multiprocessing import Process
from kafka import KafkaConsumer




def connection():
    mydb = mysql.connector.connect(
        host = "localhost",
        user = "root",
        password = "12345",
        database = "testdb"
    )
    return mydb


app = Flask("__main__")         #for windows
# app = Flask(__name__)
app.config['SECRET_KEY'] = 'sasdsd'
app.config['UPLOADED_PHOTOS_DEST'] = 'upload'
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'db+mysql://root:12345@localhost/testdb'
app.config['CELERY_TRACK_STARTED'] = True

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)



save_path = 'save_img'

topic_name = "streaming"
consumer1 = KafkaConsumer(
    topic_name,
    group_id='test0',
    bootstrap_servers=["localhost:9092"],
    auto_offset_reset='latest',
    enable_auto_commit=True,
    fetch_max_bytes=9000000,
    fetch_max_wait_ms=10000,
    api_version=(0, 10, 2)
)

consumer2 = KafkaConsumer(
    topic_name,
    group_id='test1',
    bootstrap_servers=["localhost:9092"],
    auto_offset_reset='latest',
    enable_auto_commit=True,
    fetch_max_bytes=9000000,
    fetch_max_wait_ms=10000,
    api_version=(0, 10, 2)
)

process1_run = False
process2_run = False

def base64_to_string(base64_string):
    return base64.b64decode(base64_string).decode('utf-8')

def base64_to_image(base64_string):
    image = base64.b64decode(base64_string)
    image = Image.open(io.BytesIO(image))
    image = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2RGB)
    return image


def utc2local(utc):
    epoch = mktime(utc.timetuple())
    offset = datetime.fromtimestamp(epoch) - datetime.utcfromtimestamp(epoch)
    return utc + offset

def delete(directory):
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))


def video_streaming1():
    consumer1.poll()
    consumer1.seek_to_end()
    for message in consumer1:
        # print("Da nhan 1")
        yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + message.value + b'\r\n')

def video_streaming2():
    consumer2.poll()
    consumer2.seek_to_end()
    for message in consumer2:
        # print("Da nhan 2")
        yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + message.value + b'\r\n')

@app.route('/', methods=['POST', 'GET'])
@app.route('/log_in', methods=['POST', 'GET'])
def log_in():
    session.clear()
    return render_template('log_in.html')

@app.route('/data_login', methods=['POST', 'GET'])
def data_login():
    data = request.get_json()
    result = json.loads(data)
    key_lst = list(result.keys())
    print(key_lst)
    username_base64 = result.get(key_lst[0])
    username = base64_to_string(base64_string=username_base64)
    password_base64 = result.get(key_lst[1])
    password = base64_to_string(base64_string=password_base64)
    print(username)
    print(password)
    database = connection()
    cursor = database.cursor()
    cursor.execute('SELECT name, username, password, role FROM users WHERE username = %s', (username,))
    account = cursor.fetchone()
    database.close()
    # print(type(account[2]))
    if not account:
        message = 'Account not found'
        print(message)
        return json.dumps({'success': False, 'message': 'Account not found'}), 200, {'ContentType': 'application/json'}
    else:
        if bcrypt.checkpw(password.encode('utf-8'), account[2].encode('utf-8')):
            message = 'Login success'
            print(message)
            session.clear()
            session['loggedin'] = True
            session['name'] = account[0]
            session['username'] = account[1]
            session['role'] = account[3]
            if account[3] == 'admin':
                return json.dumps({'success': True, 'role': 'admin', 'message': 'Login success'}), 200, {'ContentType': 'application/json'}
            elif account[3] == 'user':
                return json.dumps({'success': True, 'role': 'user', 'message': 'Login success'}), 200, {'ContentType': 'application/json'}
            elif account[3] == 'display':
                return json.dumps({'success': True, 'role': 'display', 'message': 'Login success'}), 200, {'ContentType': 'application/json'}
        else:
            message = 'Wrong password'
            print(message)
            return json.dumps({'success': False, 'message': 'Wrong password'}), 200, {'ContentType': 'application/json'}

@app.route('/sign_in', methods=['POST', 'GET'])
def sign_in():
    return render_template('sign_in.html')

@celery.task
def data_register_process(data, name, username, password):
    image_lst = []
    image_lst1 = []
    encode_lst = []     # dùng để kiểm tra ảnh chân dung
    encode_lst1 = []    # dùng để kiểm tra có cùng 1 người không
    vector_json = []    # dùng để lưu encode vào mysql
    result = json.loads(data)
    key_lst = list(result.keys())
    for i in range(4, 9):
        base64_img = result.get(f"{key_lst[i]}")
        img = base64_to_image(base64_string=base64_img)
        if result.get(key_lst[0]) == True:
            print("hi1")
            img = cv2.resize(img, (640, 480))
        image_lst.append(img)
    if not os.path.isdir(app.config['UPLOADED_PHOTOS_DEST'] + "/" + f"{username}-{name}"):
        os.mkdir(app.config['UPLOADED_PHOTOS_DEST'] + "/" + f"{username}-{name}")
    for i, j in enumerate(image_lst):
        is_written = cv2.imwrite(app.config['UPLOADED_PHOTOS_DEST'] + "/" + f"{username}-{name}" + "/" + f"{name}{i}.jpg", j)
        if not is_written:
            shutil.rmtree(os.path.join(app.config['UPLOADED_PHOTOS_DEST'], f"{username}-{name}"))
            return {'success': False, 'message': 'Lưu ảnh không thành công'}
    for i in range(5):
        img = cv2.imread(app.config['UPLOADED_PHOTOS_DEST'] + "/" + f"{username}-{name}" + "/" + f"{name}{i}.jpg")
        img = cv2.resize(img, (0, 0), fx=0.5, fy=0.5)
        image_lst1.append(img)
    for i in image_lst1:
        vector_encode = face_recognition.face_encodings(i)
        encode_lst.append(vector_encode)
    for i in encode_lst:
        if len(i) != 1:
            delete(os.path.join(app.config['UPLOADED_PHOTOS_DEST'], f"{username}-{name}"))
            shutil.rmtree(os.path.join(app.config['UPLOADED_PHOTOS_DEST'], f"{username}-{name}"))
            return {'success': False, 'message': 'Ảnh phải là ảnh chân dung'}
    for i in encode_lst:
        encode_lst1.append(i[0])
    matchs = face_recognition.compare_faces(encode_lst1, encode_lst1[0])
    print(matchs)
    if False in matchs:
        delete(os.path.join(app.config['UPLOADED_PHOTOS_DEST'], f"{username}-{name}"))
        shutil.rmtree(os.path.join(app.config['UPLOADED_PHOTOS_DEST'], f"{username}-{name}"))
        return {'success': False, 'message': 'Ảnh phải cùng một khuôn mặt'}
    else:
        now = datetime.now()
        time_record = now.strftime('%Y-%m-%d %H:%M:%S')
        database = connection()
        cursor = database.cursor()
        for i in range(5):
            vector_json.append(json.dumps(encode_lst[i][0].tolist()))
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        cursor.execute('INSERT INTO users VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', (name, username, hashed_password, "user", save_path + "/" + f"{username}-{name}" + "/" + f"{name}0.jpg", vector_json[0], vector_json[1], vector_json[2], vector_json[3], vector_json[4], 'None', 'None'))
        database.commit()
        cursor.execute('INSERT INTO history VALUES (%s, %s, %s, %s, %s, %s)', (name, username, time_record, "insert", "no", "account register"))
        database.commit()
        database.close()
        shutil.copytree(os.path.join(app.config['UPLOADED_PHOTOS_DEST'], f"{username}-{name}"), save_path + "/" + f"{username}-{name}")
        delete(os.path.join(app.config['UPLOADED_PHOTOS_DEST'], f"{username}-{name}"))
        shutil.rmtree(os.path.join(app.config['UPLOADED_PHOTOS_DEST'], f"{username}-{name}"))
        return {'success': True, 'message': 'Đăng ký tài khoản thành công'}


@app.route('/register', methods=['POST', 'GET'])
def register():
    data = request.get_json()
    result = json.loads(data)
    key_lst = list(result.keys())
    name_base64 = result.get(key_lst[1])
    name = base64_to_string(base64_string=name_base64)
    username_base64 = result.get(key_lst[2])
    username = int(base64_to_string(base64_string=username_base64))
    password_base64 = result.get(key_lst[3])
    password = base64_to_string(base64_string=password_base64)
    print(name)
    print(username)
    print(password)
    database = connection()
    cursor = database.cursor()
    cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
    account = cursor.fetchone()
    database.close()
    if account:
        return json.dumps({'success': False, 'message': 'Tài khoản này đã được sử dụng'}), 200, {'ContentType': 'application/json'}
    else:
        time_record = datetime.now()
        time_record = time_record.strftime('%Y-%m-%d %H:%M:%S')
        task_id = data_register_process.delay(data, name, username, password)
        task = data_register_process.AsyncResult(task_id)
        print(task.status)
        return json.dumps({'success': True, 'message': f"Thông tin được gửi thành công với\n Task_id: {task_id}\n Thời gian: {time_record}"}), 200, {'ContentType': 'application/json'}

@app.route('/search_task_id', methods=['POST'])
def search_task_id():
    data = request.get_json()
    result = json.loads(data)
    key_lst = list(result.keys())
    task_idBase64 = result.get(key_lst[0])
    task_id = base64_to_string(base64_string=task_idBase64)
    database = connection()
    cursor = database.cursor()
    cursor.execute('SELECT status, result, date_done FROM celery_taskmeta WHERE task_id = %s', (task_id,))
    result_taskid = cursor.fetchone()
    database.close()
    if result_taskid:
        if result_taskid[0] == "STARTED":
            return json.dumps({'success': False, 'message': 'Thông tin của bạn đang được xử lý'}), 200, {'ContentType': 'application/json'}
        elif result_taskid[0] == "SUCCESS":
            text = pickle.loads(result_taskid[1])
            time_zone = utc2local(result_taskid[2])
            return json.dumps({'success': True, 'message': f"Thông tin của bạn đã được xử lý\n Kết quả: {text['message']}\n Thời gian: {time_zone}"}), 200, {'ContentType': 'application/json'}
        elif result_taskid[0] == "FAILURE":
            return json.dumps({'success': False, 'message': 'Thông tin của bạn xử lý thất bại hãy gửi lại yêu cầu mới'}), 200, {'ContentType': 'application/json'}
    else:
        return json.dumps({'success': False, 'message': 'Không có thông tin tìm kiếm trong dữ liệu'}), 200, {'ContentType': 'application/json'}


@app.route('/video')
def video():
    return render_template('video.html')

@app.route('/video_feed1')
def video_feed1():
    global process1_run
    if session.get('loggedin') == None or session.get('role') == "user" or session.get('role') == "display":
        return render_template('video.html')
    else:
        if not process1_run:
            t1.start()
            process1_run = True
        return Response(video_streaming1(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/display', methods=['POST', 'GET'])
def display():
    return render_template('display.html')

@app.route('/video_feed2')
def video_feed2():
    global process2_run
    if session.get('loggedin') == None or session.get('role') == "user" or session.get('role') == "admin":
        return render_template('display.html')
    else:
        if not process2_run:
            t2.start()
            process2_run = True
        return Response(video_streaming2(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/display_images', methods=['POST'])
def display_images():
    image_lst = []
    database = connection()
    cursor = database.cursor()
    cursor.execute("SELECT * FROM attendance ORDER BY day_time DESC LIMIT 5")
    result = cursor.fetchall()
    database.close()
    for i in range(len(result)):
        day_time = result[i][2].replace(" ", "_")
        day_time = day_time.replace(":", "-")
        file_name = f"{result[i][3]}/{result[i][4]}/{result[i][0]}_{result[i][1]}_{day_time}.jpg"
        with open(file_name, "rb") as image_file:
            my_string = base64.b64encode(image_file.read())
        my_string = my_string.decode('utf-8')
        my_string = "data:image/jpeg;base64," + my_string
        image_lst.append(my_string)
    return json.dumps({'success': True, 'message': result, 'images': image_lst}), 200, {'ContentType': 'application/json'}


@app.route('/log_out', methods=['POST', 'GET'])
def log_out():
    session.pop('loggedin', None)
    session.pop('name', None)
    session.pop('username', None)
    session.pop('role', None)
    return redirect('/log_in', code=301)

@app.route('/update_password', methods=['POST','GET'])
def update_password():
    return render_template('update_password.html')

@app.route('/update_password_admin', methods=['POST', 'GET'])
def update_password_admin():
    return render_template('update_password_admin.html')

@app.route('/data_update_password', methods=['POST'])
def data_update_password():
    data = request.get_json()
    result = json.loads(data)
    key_lst = list(result.keys())
    # print(key_lst)
    oldpassword_base64 = result.get(key_lst[0])
    oldpassword = base64_to_string(base64_string=oldpassword_base64)
    newpassword_base64 = result.get(key_lst[1])
    newpassword = base64_to_string(base64_string=newpassword_base64)
    # print(oldpassword)
    # print(newpassword)
    database = connection()
    cursor = database.cursor()
    cursor.execute('SELECT name, username, password FROM users WHERE username = %s', (session['username'],))
    account = cursor.fetchone()
    # print(account)
    if bcrypt.checkpw(oldpassword.encode('utf-8'), account[2].encode('utf-8')):
        now = datetime.now()
        time_record = now.strftime('%Y-%m-%d %H:%M:%S')
        message = 'Dung pass'
        print(message)
        hashed_password = bcrypt.hashpw(newpassword.encode('utf-8'), bcrypt.gensalt())
        cursor.execute('UPDATE users SET password = %s WHERE username = %s', (hashed_password, session['username']))
        database.commit()
        cursor.execute('INSERT INTO history VALUES (%s, %s, %s, %s, %s, %s)', (session['name'], session['username'], time_record, "update", "yes", "update password"))
        database.commit()
        database.close()
        return json.dumps({'success': True, 'message': 'Change password successfully'}), 200, {'ContentType': 'application/json'}
    else:
        message = 'Sai pass'
        print(message)
        database.close()
        return json.dumps({'success': False, 'message': 'Wrong password'}), 200, {'ContentType': 'application/json'}

@app.route('/update_images', methods=['POST','GET'])
def update_images():
    return render_template('update_images.html')

@app.route('/update_images_admin', methods=['POST', 'GET'])
def update_images_admin():
    return render_template('update_images_admin.html')

@celery.task
def data_update_images_process(data, name, username):
    image_lst = []
    image_lst1 = []
    encode_lst = []         #dùng để kiểm tra ảnh chân dung
    encode_lst1 = []        #dùng để kiểm tra có cùng 1 người không
    vector_json = []        # dùng để lưu encode vào mysql
    result = json.loads(data)
    key_lst = list(result.keys())
    for i in range(1, 6):
        base64_img = result.get(f"{key_lst[i]}")
        img = base64_to_image(base64_string=base64_img)
        if result.get(key_lst[0]) == True:
            print("hi")
            img = cv2.resize(img, (640, 480))
        image_lst.append(img)
    if not os.path.isdir(app.config["UPLOADED_PHOTOS_DEST"] + "/" + f"{username}-{name}"):
        os.mkdir(app.config['UPLOADED_PHOTOS_DEST'] + "/" + f"{username}-{name}")
    for i, j in enumerate(image_lst):
        is_written = cv2.imwrite(app.config['UPLOADED_PHOTOS_DEST'] + "/" + f"{username}-{name}" + "/" + f"{name}{i}.jpg", j)
        if not is_written:
            shutil.rmtree(os.path.join(app.config['UPLOADED_PHOTOS_DEST'], f"{username}-{name}"))
            return {'success': False, 'message': 'Lưu ảnh không thành công'}
    for i in range(5):
        img = cv2.imread(app.config['UPLOADED_PHOTOS_DEST'] + "/" + f"{username}-{name}" + "/" + f"{name}{i}.jpg")
        img = cv2.resize(img, (0, 0), fx=0.5, fy=0.5)
        image_lst1.append(img)
    for i in image_lst1:
        vector_encode = face_recognition.face_encodings(i)
        encode_lst.append(vector_encode)
    for i in encode_lst:
        if len(i) != 1:
            delete(os.path.join(app.config['UPLOADED_PHOTOS_DEST'], f"{username}-{name}"))
            shutil.rmtree(os.path.join(app.config['UPLOADED_PHOTOS_DEST'], f"{username}-{name}"))
            return {'success': False, 'message': 'Ảnh phải là ảnh chân dung'}
    for i in encode_lst:
        encode_lst1.append(i[0])
    matchs = face_recognition.compare_faces(encode_lst1, encode_lst1[0])
    print(matchs)
    if False in matchs:
        delete(os.path.join(app.config['UPLOADED_PHOTOS_DEST'], f"{username}-{name}"))
        shutil.rmtree(os.path.join(app.config['UPLOADED_PHOTOS_DEST'], f"{username}-{name}"))
        return {'success': False, 'message': 'Ảnh phải cùng một khuôn mặt'}
    else:
        now = datetime.now()
        time_record = now.strftime('%Y-%m-%d %H:%M:%S')
        database = connection()
        cursor = database.cursor()
        for i in range(5):
            vector_json.append(json.dumps(encode_lst[i][0].tolist()))
        cursor.execute('UPDATE users SET vectorencode0 = %s, vectorencode1 = %s, vectorencode2 = %s, vectorencode3 = %s, vectorencode4 = %s WHERE username = %s', (vector_json[0], vector_json[1], vector_json[2], vector_json[3], vector_json[4], username))
        database.commit()
        cursor.execute('INSERT INTO history VALUES (%s, %s, %s, %s, %s, %s)', (name, username, time_record, "update", "no", "update images"))
        database.commit()
        database.close()
        delete(save_path + "/" + f"{username}-{name}")
        shutil.rmtree(save_path + "/" + f"{username}-{name}")
        shutil.copytree(os.path.join(app.config['UPLOADED_PHOTOS_DEST'], f"{username}-{name}"), save_path + "/" + f"{username}-{name}")
        delete(os.path.join(app.config['UPLOADED_PHOTOS_DEST'], f"{username}-{name}"))
        shutil.rmtree(os.path.join(app.config['UPLOADED_PHOTOS_DEST'], f"{username}-{name}"))
        return {'success': True, 'message': 'Cập nhật ảnh thành công'}

@app.route('/data_update_images', methods=['POST'])
def data_update_images():
    data = request.get_json()
    result = json.loads(data)
    key_lst = list(result.keys())
    # print(key_lst)
    name = session["name"]
    username = session["username"]
    time_record = datetime.now()
    time_record = time_record.strftime('%Y-%m-%d %H:%M:%S')
    task_id = data_update_images_process.delay(data, name, username)
    task_id_str = str(task_id)
    database = connection()
    cursor = database.cursor()
    cursor.execute("SELECT task_id, time_send FROM users WHERE name = %s AND username = %s", (name, username))
    result = cursor.fetchone()
    task_id_list = []
    time_send_list = []
    if result[0] == "None":
        task_id_list.append(task_id_str)
        time_send_list.append(time_record)
        cursor.execute('UPDATE users SET task_id = %s, time_send = %s WHERE username = %s', (json.dumps(task_id_list), json.dumps(time_send_list), username))
        database.commit()
        database.close()
    else:
        task_id_list = json.loads(result[0])
        time_send_list = json.loads(result[1])
        if len(task_id_list) == 5:
            task_id_list.pop(0)
            time_send_list.pop(0)
        task_id_list.append(task_id_str)
        time_send_list.append(time_record)
        cursor.execute('UPDATE users SET task_id = %s, time_send = %s WHERE username = %s', (json.dumps(task_id_list), json.dumps(time_send_list), username))
        database.commit()
        database.close()
    return json.dumps({'success': True, 'message': f"Thông tin được gửi thành công với\n Task_id: {task_id}\n Thời gian: {time_record}"}), 200, {'ContentType': 'application/json'}

@app.route('/task_id_process', methods=['POST'])
def task_id_process():
    name = session['name']
    username = session['username']
    database = connection()
    cursor = database.cursor()
    cursor.execute("SELECT task_id, time_send FROM users WHERE username = %s", (username,))
    result = cursor.fetchone()
    if result[0] == "None":
        database.close()
        return json.dumps({'data': False, 'message': 'Không có dữ liệu'}), 200, {'ContentType': 'application/json'}
    else:
        result_list = []
        task_id_list = json.loads(result[0])
        task_id_list = task_id_list[::-1]
        time_send_list = json.loads(result[1])
        time_send_list = time_send_list[::-1]
        for i, j in zip(task_id_list, time_send_list):
            cursor.execute("SELECT status, result, date_done FROM celery_taskmeta WHERE task_id = %s", (i,))
            data = cursor.fetchone()
            text = pickle.loads(data[1])
            time_zone = utc2local(data[2])
            result_tuple = (i, data[0], text['message'], f"{j}", f"{time_zone}")
            result_list.append(result_tuple)
        database.close()
        return json.dumps({'data': True, 'message': result_list}), 200, {'ContentType': 'application/json'}

@app.route('/time', methods=['POST','GET'])
def time():
    return render_template('time.html')

@app.route('/time_admin', methods=['POST', 'GET'])
def time_admin():
    return render_template('time_admin.html')

@app.route('/data_time', methods=['POST'])
def data_time():
    image_lst = []
    data = request.get_json()
    data = json.loads(data)
    key_lst = list(data.keys())
    countBase64 = data.get(f"{key_lst[0]}")
    count = int(base64_to_string(base64_string=countBase64))
    # print(count)
    database = connection()
    cursor = database.cursor()
    cursor.execute('SELECT * FROM attendance WHERE username = %s ORDER BY day_time DESC LIMIT %s', (session['username'], count))
    result = cursor.fetchall()
    database.close()
    # print(type(data))
    if len(result) == 0:
        return json.dumps({'success': False, 'message': 'Không có dữ liệu người dùng'}), 200, {'ContentType': 'application/json'}
    else:
        for i in range(len(result)):
            day_time = result[i][2].replace(" ", "_")
            day_time = day_time.replace(":", "-")
            file_name = f"{result[i][3]}/{result[i][4]}/{result[i][0]}_{result[i][1]}_{day_time}.jpg"
            with open(file_name, "rb") as image_file:
                my_string = base64.b64encode(image_file.read())
            my_string = my_string.decode('utf-8')
            my_string = "data:image/jpeg;base64," + my_string
            image_lst.append(my_string)
        return json.dumps({'success': True, 'message': result, 'images': image_lst}), 200, {'ContentType': 'application/json'}

@app.route('/search', methods=['POST', 'GET'])
def search():
    return render_template('search.html')

@app.route('/data_search', methods=['POST'])
def data_search():
    image_lst = []
    data = request.get_json()
    data = json.loads(data)
    key_lst = list(data.keys())
    select_typeBase64 = data.get(f"{key_lst[0]}")
    select_type = base64_to_string(base64_string=select_typeBase64)
    if select_type == "name-username":
        queryBase64 = data.get(f"{key_lst[1]}")
        query = base64_to_string(base64_string=queryBase64)
        countBase64 = data.get(f"{key_lst[2]}")
        count = int(base64_to_string(base64_string=countBase64))
        # print(query)
        # print(f"{key_lst[2]}",count)
        database = connection()
        cursor = database.cursor()
        cursor.execute("SELECT name, username, role FROM users WHERE (name LIKE '%{}%' OR username LIKE '%{}%') AND role NOT IN ('display')".format(query, query))
        result_all = cursor.fetchall()
        cursor.execute("SELECT name, username, role, image_path FROM users WHERE (name LIKE '%{}%' OR username LIKE '%{}%') AND role NOT IN ('display') LIMIT {}".format(query, query, count))
        result = cursor.fetchall()
        # print(result)
        database.close()
        if len(result_all) == 0:
            return json.dumps({'success': False, 'message': 'Không có dữ liệu người dùng'}), 200, {'ContentType': 'application/json'}
        else:
            for i in range(len(result)):
                file_name = result[i][3]
                with open(file_name, "rb") as image_file:
                    my_string = base64.b64encode(image_file.read())
                my_string = my_string.decode('utf-8')
                my_string = "data:image/jpeg;base64," + my_string
                image_lst.append(my_string)
            return json.dumps({'success': True, 'message': result, 'images': image_lst, 'length': len(result_all)}), 200, {'ContentType': 'application/json'}
    elif select_type == "time":
        time_fromBase64 = data.get(f"{key_lst[1]}")
        time_from = base64_to_string(base64_string=time_fromBase64)
        time_toBase64 = data.get(f"{key_lst[2]}")
        time_to = base64_to_string(base64_string=time_toBase64)
        time_from = time_from.replace("T", " ")
        time_to = time_to.replace("T", " ")
        countBase64 = data.get(f"{key_lst[3]}")
        count = int(base64_to_string(base64_string=countBase64))
        # print(f"{key_lst[3]}", count)
        # print("time_from", time_from)
        # print("time_to", time_to)
        database = connection()
        cursor = database.cursor()
        cursor.execute("SELECT * FROM attendance WHERE day_time BETWEEN '{}' AND '{}' ORDER BY day_time DESC".format(time_from, time_to))
        result_all = cursor.fetchall()
        cursor.execute("SELECT * FROM attendance WHERE day_time BETWEEN '{}' AND '{}' ORDER BY day_time DESC LIMIT %s".format(time_from, time_to), (count,))
        result = cursor.fetchall()
        database.close()
        if len(result_all) == 0:
            return json.dumps({'success': False, 'message': 'Thông tin tìm kiếm không có trong dữ liệu'}), 200, {'ContentType': 'application/json'}
        else:
            for i in range(len(result)):
                day_time = result[i][2].replace(" ", "_")
                day_time = day_time.replace(":", "-")
                file_name = f"{result[i][3]}/{result[i][4]}/{result[i][0]}_{result[i][1]}_{day_time}.jpg"
                with open(file_name, "rb") as image_file:
                    my_string = base64.b64encode(image_file.read())
                my_string = my_string.decode('utf-8')
                my_string = "data:image/jpeg;base64," + my_string
                image_lst.append(my_string)
            return json.dumps({'success': True, 'message': result, 'images': image_lst, 'length': len(result_all)}), 200, {'ContentType': 'application/json'}

@app.route('/view_user_modal', methods=['POST'])
def view_user_modal():
    image_lst = []
    data = request.get_json()
    data = json.loads(data)
    key_lst = list(data.keys())
    nameBase64 = data.get(f"{key_lst[0]}")
    name = base64_to_string(base64_string=nameBase64)
    usernameBase64 = data.get(f"{key_lst[1]}")
    username = base64_to_string(base64_string=usernameBase64)
    # print(name)
    # print(username)
    database = connection()
    cursor = database.cursor()
    cursor.execute("SELECT day_time, image_path, real_fake FROM attendance WHERE name = %s AND username = %s ORDER BY day_time DESC LIMIT 5", (name, username))
    result = cursor.fetchall()
    database.close()
    for i in range(len(result)):
        day_time = result[i][0].replace(" ", "_")
        day_time = day_time.replace(":", "-")
        file_name = f"{result[i][1]}/{result[i][2]}/{name}_{username}_{day_time}.jpg"
        with open(file_name, "rb") as image_file:
            my_string = base64.b64encode(image_file.read())
        my_string = my_string.decode('utf-8')
        my_string = "data:image/jpeg;base64," + my_string
        image_lst.append(my_string)
    return json.dumps({'success': True, 'message': result, 'name': name, 'username': username, 'images': image_lst}), 200, {'ContentType': 'application/json'}

@app.route('/download_excel_api', methods=['POST'])
def downloadExcelApi():
    data = request.get_json()
    select_type = data.get("type")
    print(select_type)
    result = 0
    database = connection()
    cursor = database.cursor()
    if select_type == "name-username":
        name = data.get("name")
        username = data.get("username")
        cursor.execute("SELECT * FROM attendance WHERE name = %s AND username = %s ORDER BY day_time DESC", (name, username))
        result = cursor.fetchall()
    elif select_type == "time":
        time_from = data.get("from")
        time_from = time_from.replace("T", " ")
        time_to = data.get("to")
        time_to = time_to.replace("T", " ")
        cursor.execute("SELECT * FROM attendance WHERE day_time BETWEEN '{}' AND '{}' ORDER BY day_time DESC".format(time_from, time_to))
        result = cursor.fetchall()
    database.close()
    if len(result) == 0:
        return {'success': False, 'message': 'Thông tin tìm kiếm không có trong dữ liệu'}

    else:
        buffer = BytesIO()
        workbook = xlsxwriter.Workbook(buffer)
        worksheet = workbook.add_worksheet()
        format_style = workbook.add_format({'bold': True})
        format_style_real = workbook.add_format({'bold': True, 'font_color': 'green'})
        format_style_fake = workbook.add_format({'bold': True, 'font_color': 'red'})
        worksheet.write(0, 0, "name", format_style)
        worksheet.write(0, 1, "username", format_style)
        worksheet.write(0, 2, "day_time", format_style)
        worksheet.write(0, 3, "Real/Fake", format_style)
        for i, j in enumerate(result):
            worksheet.write(i+1, 0, j[0])
            worksheet.write(i+1, 1, f"{j[1]}")
            worksheet.write(i+1, 2, j[2])
            if j[4] == "real":
                worksheet.write(i+1, 3, j[4], format_style_real)
            else:
                worksheet.write(i + 1, 3, j[4], format_style_fake)
        workbook.close()
        buffer.seek(0)
        file = buffer.read()
        unicodeBase64File = base64.b64encode(file).decode("utf-8")
        response = {'success': True, 'data': [unicodeBase64File]}
        return response

@app.route('/delete_account', methods=['POST'])
def delete_account():
    data = request.get_json()
    data = json.loads(data)
    key_lst = list(data.keys())
    nameBase64 = data.get(f"{key_lst[0]}")
    name = base64_to_string(base64_string=nameBase64)
    usernameBase64 = data.get(f"{key_lst[1]}")
    username = base64_to_string(base64_string=usernameBase64)
    database = connection()
    cursor = database.cursor()
    cursor.execute("SELECT * FROM users WHERE name = %s AND username = %s", (name, username))
    result = cursor.fetchone()
    if result:
        now = datetime.now()
        time_record = now.strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("DELETE FROM users WHERE name = %s AND username = %s", (name, username))
        database.commit()
        cursor.execute('INSERT INTO history VALUES (%s, %s, %s, %s, %s, %s)', (name, username, time_record, "delete", "no", "delete account"))
        database.commit()
        database.close()
        # index = ten.index(f"{name}-{username}")
        # del ten[index]
        # del mahoalist[index]
        delete(save_path + "/" + f"{username}-{name}")
        shutil.rmtree(save_path + "/" + f"{username}-{name}")
        return json.dumps({'success': True, 'message': 'Xóa thành công'}), 200, {'ContentType': 'application/json'}
    else:
        database.close()
        return json.dumps({'success': False, 'message': 'Thông tin tìm kiếm không có trong dữ liệu'}), 200, {'ContentType': 'application/json'}


@app.route('/check_login', methods=['POST'])
def check_login():
    if session.get('loggedin') == None:
        return json.dumps({'login': False, 'message': 'Hãy đăng nhập lại'}), 200, {'ContentType': 'application/json'}
    else:
        if session['role'] == 'user':
            return json.dumps({'login': True, 'role': 'user'}), 200, {'ContentType': 'application/json'}
        elif session['role'] == 'admin':
            return json.dumps({'login': True, 'role': 'admin'}), 200, {'ContentType': 'application/json'}
        elif session['role'] == 'display':
            return json.dumps({'login': True, 'role': 'display'}), 200, {'ContentType': 'application/json'}


if __name__ == '__main__':
    t1 = Process(target=video_streaming1, args=())
    t2 = Process(target=video_streaming2, args=())
    app.run(host="0.0.0.0", ssl_context="adhoc")
    # ngrok.set_auth_token("2OSzh7c2wxBhr1QLZXs8fkW2nbV_2h2hxWA7mwdKVVFsByZ4H")
    # port_number = 5000
    # public_url = ngrok.connect(5000).public_url
    # print(public_url)
    # app.run(port=port_number)


