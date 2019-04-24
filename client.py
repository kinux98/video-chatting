#-*- coding:utf-8 -*-
import socket
import threading
import pyaudio
import json
import base64
import os
import numpy as np
import cv2

# record
MONO = 1
RATE = 44100
CHUNK = int(RATE / 10)
FORMAT = pyaudio.paInt16
p = pyaudio.PyAudio()
send_cnt = False

exit_flag = False
lock = threading.Lock() 
cap = cv2.VideoCapture(0)

def recvall_voice(sock):
    BUFF_SIZE = 4096 # 4 KiB
    data = b''
    while True:
        part = sock.recv(BUFF_SIZE)
        data += part
        if len(part) < BUFF_SIZE:
            # either 0 or end of data
            break
    return data
def recvall_video(sock):
    BUFF_SIZE = 409600 # 4 KiB
    data = b''
    while True:
        part = sock.recv(BUFF_SIZE)
        if not part:
            return 0xdeadbeef
        data += part
        if len(part) < BUFF_SIZE:
            # either 0 or end of data
            break
    return data
def recvall_text(sock):
    BUFF_SIZE = 4096 # 4 KiB
    data = b''
    while True:
        part = sock.recv(BUFF_SIZE)
        data += part
        if len(part) < BUFF_SIZE:
            # either 0 or end of data
            break
    return data
def select_device(): # reference :  https://gist.github.com/mansam/9332445
    os.system('cls')
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    for i in range (0,numdevices):
            if p.get_device_info_by_host_api_device_index(0,i).get('maxInputChannels')>0:
                    print ("Input Device  id   " +  str(i) +  " - " + str(p.get_device_info_by_host_api_device_index(0,i).get('name')))
            if p.get_device_info_by_host_api_device_index(0,i).get('maxOutputChannels')>0:
                    print ("Output Device id   " +  str(i) +  " - " + str(p.get_device_info_by_host_api_device_index(0,i).get('name')))

    devinfo = p.get_device_info_by_index(1)
    if p.is_format_supported(44100.0,  # Sample rate
                         input_device=devinfo["index"],
                         input_channels=devinfo['maxInputChannels'],
                         input_format=pyaudio.paInt16):
        print ("Recommended device is ",devinfo.get('name'))

    while True:                     
        input_idx = int(input("Please select input device id : "))
        output_idx = int(input("Please select output device id : "))
        if((input_idx >= 0 and input_idx <= numdevices) and (output_idx >= 0 and output_idx <= numdevices)):
            os.system('cls')
            return (input_idx, output_idx)
        else:
            continue  
# get msg from server 
def get_msg(s):
    while 1:
        try:
            msg = recvall_text(s).decode()   #
            message = "[{}]".format(msg[:-len(", ")])
            commands = json.loads(message)
            for cmd in commands:
                if  cmd["command"] == "text":
                    text_msg = cmd["chatting"]
                    print(text_msg)
        except:
            exit(0)
def get_voice(s_voice, output_idx):
    out_stream = p.open(format=FORMAT,
                        channels=MONO,
                        rate=RATE,
                        output=True,
                        output_device_index = output_idx)
    while 1:
        try:
            data = recvall_voice(s_voice)
            #print(data)
            data = data.decode()
            data = base64.b64decode(data)
            out_stream.write(data)
        except:
            exit(0)   
# sendall voice data to server
def voice_connect(s_voice, input_idx, output_idx):
    t = threading.Thread(target=get_voice, args=[s_voice, output_idx])
    t.daemon = True
    t.start()

    in_stream = p.open(format=FORMAT,
                       channels=MONO,
                       rate=RATE,
                       input=True,
                       input_device_index = input_idx)
    while 1:
        try:
            data = in_stream.read(CHUNK)
            outut_data = base64.b64encode(data).decode()
            s_voice.sendall((outut_data).encode())
        except:
            exit(0)
    exit(0)
def get_video(s_video_get):
    while 1:
        try:
            frame = recvall_video(s_video_get)
            if frame == 0xdeadbeef:
                break
            img = base64.b64decode(frame)
            npimg = np.frombuffer(img, dtype=np.uint8)
            source = cv2.imdecode(npimg, 1)
            cv2.imshow("Opponent's face", source)
            if cv2.waitKey(1) & 0xff == 27 :
                break
        except:
            continue
    exit(0)
           

def send_video(s_video_send):
    while 1:
        try:
            ret, frame = cap.read()
            frame = cv2.resize(frame, (640, 480))
            frame = cv2.flip(frame,1)
            encoded, buffer = cv2.imencode('.jpg', frame)
            jpg_as_text = base64.b64encode(buffer).decode()
            s_video_send.sendall(jpg_as_text.encode())
        except:
            continue

def video_connect(s_video_send, s_video_get):
    t = threading.Thread(target=get_video, args=[s_video_get]) 
    t_2 = threading.Thread(target=send_video, args=[s_video_send])    
    t.daemon = True
    t_2.daemon = True
    t.start()
    t_2.start()

    while(True):
        try:
            # Capture frame-by-frame
            ret, frame = cap.read()
            frame = cv2.resize(frame, (640, 480))
            frame = cv2.flip(frame,1)
            name = "Your face"
            cv2.imshow(name, frame)
            k = cv2.waitKey(1)
            if k == 27:
                cap.release()
                t_2.exit()
                s_video_get.close()
                cv2.destroyWindow("Your face")
                s_video_send.close()
                exit(0)
        except:
            cap.release()
            s_video_get.close()
            cv2.destroyWindow("Your face")
            s_video_send.close()
            exit(0)
        
# get user input and sendall to server
def text_connect(s, ADDR):
    print ("Voice Chatting program Client!")
    print ("server connected! (enter quit to exit)")
    
    t = threading.Thread(target=get_msg, args=[s])
    t.daemon = True
    t.start() # start get_msg thread

    flag_voice = False

    input_idx, output_idx = select_device()
    s_voice = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s_voice.connect((ADDR, 15789))

    s_video_send = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s_video_send.connect((ADDR, 15800))

    s_video_get = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s_video_get.connect((ADDR, 15851))
    

    t_v = threading.Thread(target=voice_connect, args=[s_voice, input_idx, output_idx])
    t_v.daemon = True
   
    t_video = threading.Thread(target=video_connect, args=[s_video_send, s_video_get])
    t_video.daemon = True

    print("[start Chatting]")
    usrname = input("What is your name? : ")
    data = json.dumps({"command": "text", "chatting":usrname})
    s.sendall((data+ ", ").encode())

    t_v.start()
    t_video.start()
    
    while 1:    
        msg = input()
        if (msg == "quit"): # when user input is'quit', exit
            data = json.dumps({"command": "text", "chatting":msg})
            s.sendall((data+ ", ").encode())
            break
        data = json.dumps({"command": "text", "chatting":msg})
        s.sendall((data+ ", ").encode())
    
    s_voice.close()
    s.close()
    exit(0)    


# connect to localhost's 3030 port
if __name__ == '__main__':
    ADDR = input("Input the address(localhost is default) : ")
    if ADDR == "":
        ADDR = "localhost"
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ADDR, 3032))
    text_connect(s, ADDR)
