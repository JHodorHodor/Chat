#! /usr/bin/python3
import socket, sys, threading, time, struct

PORT = 40702
HOST = "localhost"
lock = threading.Lock()

class ClientThread(threading.Thread):
    
    def __init__(self, sock, server):
        threading.Thread.__init__(self)
        self.sock = sock
        self.server = server

    def mySend(self, addr, msg):
        msg = msg.encode()
        addr.send(struct.pack("i", len(msg)) + msg)

    def myRecv(self):
        try:
            size = struct.unpack("i", self.sock.recv(struct.calcsize("i")))[0]
        except:
            return None
        data = ""
        while len(data) < size:
            msg = self.sock.recv(size - len(data))
            if not msg:
                return None
            data += msg.decode()
        return data

    def sendAll(self, msg, noinfo = False):
        lock.acquire()
#--------SYNC(
        if not noinfo: 
            msg = self.name + " => ALL:\n" + msg + "\n"

        for client in self.server.clients:
            if str(client) != self.name:
                addr = self.server.clients[client]
                self.mySend(addr, msg)
#--------)SYNC
        lock.release()

    def sendTo(self, msg, to, noinfo = False):
        lock.acquire()
#--------SYNC(
        if self.name == to: 
            addr = self.sock
        else:
            addr = self.server.clients[to]
        if not noinfo: 
            msg = self.name + " => " + to + ":\n" + msg + "\n"
        self.mySend(addr, msg)
#--------)SYNC
        lock.release()

    def run(self):
        data = self.myRecv() #First pack of data contains only the name
        self.name = data

        if self.name in self.server.clients: #user already exists
            self.sendTo("BAD", self.name, True)
            return None
        else:
            self.sendTo("OK", self.name, True)

        print("New user:", data)

        for client in self.server.clients: 
            self.sendTo(client, self.name, True) #Update self list of clients
        self.sendAll(self.name, True) #Update lists of the rest of users
        
        lock.acquire()
#--------SYNC(
        self.server.clients.update({self.name : self.sock}) #New client
#--------)SYNC
        lock.release()

        while 1:
            try:
                txt = self.myRecv()
                print("rec:", txt)
                if txt is None:
                    break
                elif txt[0] == "!": #User has disconnected
                    self.sendAll(txt, True)
                else:
                    to = txt[:txt.find(" ")]
                    msg = txt[txt.find(" ") + 1:]
                    if to == "ALL":
                        self.sendAll(msg)
                    else:
                        self.sendTo(msg, to)

            except Exception as e:
                print(e)
                if len(txt) == 0:
                    break
        print("CLOSING", self.name)        
        lock.acquire()
#--------SYNC(
        self.server.clients.pop(self.name)
#--------)SYNC
        lock.release()
        self.sendAll("!" + self.name, True)
        self.sock.close()


class Server(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.bind((HOST, PORT))
        self.serverSocket.listen(1)
        self.clients = dict()

    def run(self):
        while 1:
            clientSocket, addr = self.serverSocket.accept()
            print ("Got a new connection from: ", addr)
            clientThread = ClientThread(clientSocket, self)
            clientThread.start()
        self.serverSocket.close()

s = Server()
s.start()