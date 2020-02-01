#! /usr/bin/python3
from tkinter import *
import socket, sys, threading, queue, time, struct

PORT = 40702
HOST = "localhost"
changes = queue.Queue()
listLock = threading.Lock()

class LogIn(threading.Thread):
    
    def __init__(self):
        window = Tk()
        window.title("Type your name:")

        login = Entry(window)
        login.grid(column = 1, row = 0, sticky = N + S + W + E)

        submit = Button(window, text = "Submit")
        submit.bind("<Button-1>", lambda event: self.logIn(login, window))
        submit.grid(column = 2, row = 0, sticky = N + S + W + E)

        window.mainloop()

    def logIn(self, login, window):
        name = login.get()
        if len(name) == 0 or len(name) > 30 or name.find(" ") != -1 or name.find("!") != -1 or name == "ALL":
            from tkinter import messagebox
            messagebox.showerror("Alert", "Bad name format. Chose another name")
            return None
        conn = Connection(name)
        conn.mySend(name)
        answer = conn.myRecv()
        if answer == "OK":
            self.username = name
            self.connection = conn
            window.destroy()
        elif answer == "BAD":
            conn.sock.close()            
            from tkinter import messagebox
            messagebox.showerror("Alert", "Such user already is in the Chatroom.Chose another name")
            return None
        else:
            print("Fatal error :(")


class Chat:

    def __init__(self, name, conn):
        self.name = name
        self.connection = conn
        self.addlist = []
        self.removelist = []

    def leave(self, window):
        window.destroy()

    def sendMessage(self, messageField):
        msg = messageField.get()
        if msg == "":
            from tkinter import messagebox
            messagebox.showerror("Alert", "You can't send an empty message!!!")
            return None
        user = self.userlist.get(ACTIVE)
        
        print("sent", msg, "to", user)
        rawmsg = user + " " + msg
        self.connection.mySend(rawmsg)

        self.history.config(state = "normal")
        self.history.insert(END, self.name + " => " + user + ":\n" + msg + "\n")
        self.history.config(state = "disabled")
        
        messageField.delete(0, "end")

    def dojob(self):
        self.window = Tk()
        window = self.window
        window.title("Chat: " + self.name)

        #History of the chat
        self.history = Text(window, state = "disabled")
        self.history.grid(column = 1, row = 0, sticky = N + S + W + E)
        self.receive = Receive(self.connection.sock, self)
        self.receive.daemon = True
        self.receive.start()

        #Message input
        def limitSize(*args):
            value = messageVal.get()
            if len(value) > 1000: messageVal.set(value[:1000])
        messageVal = StringVar()
        messageVal.trace('w', limitSize)
        message = Entry(window, textvariable = messageVal)
        message.bind("<Return>", lambda event: self.sendMessage(message))
        message.grid(column = 1, row = 1, sticky = N + S + W + E)

        #Users list
        self.userlist = Listbox(window)
        self.userlist.grid(column = 2, row = 0, sticky = N + S + W + E)
        self.userlist.insert(END, "ALL")

        #Send Button
        send = Button(window, text = "Send Message")
        send.bind("<Button-1>", lambda event: self.sendMessage(message))
        send.grid(column = 1, row = 3, sticky = N + S + W + E)

        #Exit button
        leave = Button(window, text = "Exit")
        leave.bind("<Button-1>", lambda event: self.leave(window))
        leave.grid(column = 2, row = 3, sticky = N + S + W + E)
        
        #Start!
        self.periodicCall()
        window.mainloop()

    def periodicCall(self):

        while changes.qsize():
                    try:
                        msg = changes.get(0)
                        if len(msg) is 0: #userlist needs to be updated

                            listLock.acquire()
#--------SYNC(
                            for item in self.removelist:
                                idx = self.userlist.get(0, END).index(item)
                                self.userlist.delete(idx)
                            self.removelist = []
                            for item in self.addlist:
                                self.userlist.insert(END, item)
                            self.addlist = []
#--------)SYNC
                            listLock.release()

                        else:
                            self.history.config(state = "normal")
                            self.history.insert(END, msg)
                            self.history.config(state = "disabled")

                    except:
                        pass
        self.window.after(1000, self.periodicCall)


class Connection:

    def __init__(self, name):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        address = HOST, PORT
        self.sock.connect(address)

    def mySend(self, msg):
        msg = msg.encode()
        self.sock.send(struct.pack("i", len(msg)) + msg)

    def myRecv(self):
        size = struct.unpack("i", self.sock.recv(struct.calcsize("i")))[0]
        data = ""
        while len(data) < size:
            msg = self.sock.recv(size - len(data))
            if not msg:
                return None
            data += msg.decode()
        return data


class Receive(threading.Thread):

    def __init__(self, sock, chat):
        threading.Thread.__init__(self)
        self.sock = sock
        self.chat = chat

    def myRecv(self):
        size = struct.unpack("i", self.sock.recv(struct.calcsize("i")))[0]
        data = ""
        while len(data) < size:
            msg = self.sock.recv(size - len(data))
            if not msg:
                return None
            data += msg.decode()
        return data

    def run(self):
        while 1:
            try:
                txt = self.myRecv()
                if txt == None: break
                print(txt)

                listLock.acquire()
#--------SYNC(
                if txt[0] == "!": #user removed
                    self.chat.removelist.append(txt[1:])
                    changes.put("") #meaning that userList has to be updated
                elif txt.find(" ") == -1: #user added (only username)
                    self.chat.addlist.append(txt)
                    changes.put("") #meaning that userList has to be updated
                else: #message incoming
                    changes.put(txt)
#--------)SYNC
                listLock.release()

            except Exception as e:
                print(e)
                break
        print("CLOSED")
        self.sock.close()

li = LogIn()
chat = Chat(li.username, li.connection)
chat.dojob()