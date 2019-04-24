import socket 
import threading
import base64
import json
import time

users = list() # users list
lock = threading.Lock() # lock for users

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

def recvall_voice(sock):
    BUFF_SIZE = 40960 # 4 KiB
    data = b''
    while True:
        part = sock.recv(BUFF_SIZE)
        data += part
        if len(part) < BUFF_SIZE:
            # either 0 or end of data
            break
    return data

def recvall_video(sock):
    BUFF_SIZE = 4096000 # 4 KiB
    data = b''
    while True:
        part = sock.recv(BUFF_SIZE)
        data += part
        if len(part) < BUFF_SIZE:
            # either 0 or end of data
            break
    return data


def voice_connect(s_voice, username, con_voice):
    print("voice server started")
    print ("voice server address : ", con_voice)

    print("%dth voice connection accepted" %(len(users)))
    while 1:
        try:
            msg = recvall_voice(con_voice).decode()
            for user in users:
                if str(user[0]) != str(username):
                    data = msg 
                    user[2].sendall((data).encode())
        except:
                exit(0)

def video_connect(s_video_send, username, con_video_send, con_video_get):
    print("Video server started")
    print("Video server addr : ", con_video_send)

    print("%dth video connection accepted" %(len(users)))
    while 1:
        try:
            video = recvall_video(con_video_send)
            for user in users:
                if str(user[0]) != str(username):
                    user[4].sendall((video))
        except:
            exit(0)

def text_connect(s, s_voice, s_video_send, s_video_get):
    con, _ = s.accept()
    print("%dth connection accepted" %(len(users) + 1))
    t = threading.Thread(target=text_connect, args=[s, s_voice, s_video_send, s_video_get])
    t.start() # when connection established, make new waiting thread

    try:
        print ("address", con)
        user_name_flag = True
        while user_name_flag:
            data = recvall_text(con).decode()
            read_msg = "[{}]".format(data[:-len(", ")])
            commands = json.loads(read_msg)
            for cmd in commands:
                if cmd["command"] == "text":
                    username = cmd["chatting"].strip() # get username
                    user_name_flag = False


        if username != "":
            con_voice, _ = s_voice.accept()
            con_video_send, _ = s_video_send.accept()
            con_video_get, _ = s_video_get.accept()
            
        tuple_4 = (username, con, con_voice, con_video_send, con_video_get)
        lock.acquire() # critical section for shared object
        users.append(tuple_4)
        lock.release()

        print (users)
        t_v = threading.Thread(target=voice_connect, args=[s_voice, username, con_voice])
        t_video = threading.Thread(target=video_connect, args=[s_video_send, username, con_video_send, con_video_get])

        t_v.daemon = True
        t_video.daemon = True

        t_video.start()
        t_v.start()
        
        for user in users: # let other users know someone entered chat
            txt = username + "has entered chat"
            data = json.dumps({"command": "text", "chatting":txt})
            user[1].sendall((data + ", ").encode())
        print (username, "connected")

        while 1:
            msg = recvall_text(con).decode()
            print(msg)
            msg = "[{}]".format(msg[:-len(", ")])
            commands = json.loads(msg)
            for cmd in commands:
                if cmd["command"] == "text":
                    msg = cmd["chatting"]
                    if (msg[0:4] == "quit"): # when user sent 'quit' then exit this thread
                        break
                    print (username + ' : ' + msg)
                    for user in users: # get msg and send to all user
                        if str(user[0]) != str(username):
                            txt = (username + " : " + msg) 
                            data = json.dumps({"command": "text", "chatting":txt})   
                            user[1].sendall((data + ", ").encode())

    except: # when exception(connection close, etc) occured, then remove user 
        remove_user(tuple_4)
    else: # user sent quit
        remove_user(tuple_4)
    exit(0) 
        

def remove_user(tuple_4):
    username, con, con_voice, con_video_send, con_video_get = tuple_4
    lock.acquire() # critial section
    users.remove(tuple_4)
    lock.release()
    print ("user \'%s\' removed" %username)
    for user in users: # let others know someone leaved the chat
        data = json.dumps({"command": "text", "chatting": (username + " has leaved chat")})   
        user[1].sendall((data+", ").encode())
    con.close()
    con_voice.close()
    con_video_send.close()
    con_video_get.close()


if __name__ == '__main__':
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 3032)) # bind localhost, port 3030
    s.listen(1)
    # start server

    s_voice = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s_voice.bind(('', 15789))
    s_voice.listen(1)

    s_video_send = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s_video_send.bind(('', 15800))
    s_video_send.listen(1)

    s_video_get = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s_video_get.bind(('', 15851))
    s_video_get.listen(1)

    t = threading.Thread(target=text_connect, args=[s, s_voice, s_video_send, s_video_get])
    t.start() # when connection established, make new waiting thread
    print("text server started")

