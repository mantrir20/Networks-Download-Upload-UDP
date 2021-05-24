import sys
import socket
import math
import hashlib
import pickle
import os
import time

host = '127.0.0.1'
port = 5000

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print("Server socket initialized")
    s.bind((host, port))
    s.settimeout(5)
    #s.setblocking(0)
    print("Successful binding. Waiting for Client now.")
except socket.error:
    print("Failed to create socket")
    sys.exit()

#return packet
def buildPacket(msg,opcode,seq_num,fname):
    print("start packet build")
    #Creating Header
    header = {}
    header['port_s'] = 420
    header['port_d'] = 5000
    header['length'] = len(msg)
    #creating Checksum
    checksum = '' + str(len(msg)) + str(header['port_s']) + str(header['port_d'])
    checksum = hashlib.md5(checksum.encode())
    checksum = checksum.hexdigest()
    header['checksum'] = checksum
    #print(header)
    #creating packet
    packet = {}
    packet['header'] = header
    packet['opcode'] = opcode
    packet['SeqNo'] = seq_num
    packet['FileName'] = fname
    packet['TID'] = 5000 # Taking as destination port
    #packet['DataBody'] = msg.encode('utf-8')
    packet['DataBody'] = msg
    return packet


def recvreply():
    recvd = False
    try:
        ClientData_flat, clientAddr = s.recvfrom(4096)
        ClientData = pickle.loads(ClientData_flat)
        recvd = True
    except ConnectionResetError:
        print("Error. Port numbers not matching. Exiting. Next time enter same port numbers.")
        #sys.exit()
    except:
        print("Timeout or some other error")
        #sys.exit()
    #text = ClientData['DataBody'].decode('utf8')
    if recvd==False:
        emsg = {}
        emsg['header']="empty"
        return emsg,"error"
    else:
        text = ClientData
        return text,clientAddr;
    
def InvalidRequest(t2,CA):
    msg = "Error: You asked for: " + \
        t2[0] + " which is not understood by the server."

    # buildPacket
    message = buildPacket(msg, 1, 1, fname)
    MESSAGE = pickle.dumps(message)
    s.sendto(MESSAGE, CA)
    print("Invalid request message sent.")
    
def handshake(t2,CA):
    print("start shake")
    msg = "okay I am ready"
    #call build packet then encode packet
    
    try:
        # buildPacket
        message = buildPacket(msg, 1, 1, fname)
        MESSAGE = pickle.dumps(message)
        s.sendto(MESSAGE, CA)
    
    except:
        print("no send work")
    print("Message Sent to Client.")
    Upload(t2)
    time.sleep(10)
    
def Upload(t2,CA):
    print("Message Sent to Client.")
    fname=""
    # start receiving
    if t2[0] == "upload":
        print("In Server, upload function")
        saveloc = "./downloads/"+t2[1]
        BigSAgain = open(saveloc, "wb")
        d = 0
        count = 0
        num = 0
        print("Receiving number of packets first.")
        while True:
            Count_full, countaddress = recvreply() # num packets
            if Count_full['header']=="empty": # this means that we have not recvd #pkts so we need an ACK for upload again
                msg = "ACK updown"
                message = buildPacket(msg, 1, 1, fname)
                MESSAGE = pickle.dumps(message)
                s.sendto(MESSAGE, CA)
                continue
            else:
                Count = Count_full['DataBody']
                t2 = Count.split()
                if t2[0]!="Number":
                    continue
                try:
                    num = int(t2[1])
                    print("Num of packets "+Count)
                    print("Receiving packets will start now if file exists.")
                    break
                except:
                    continue
        #ACK for num packets
        msg = "ACK start"
        message = buildPacket(msg, 1, 1, fname)
        MESSAGE = pickle.dumps(message)
        s.sendto(MESSAGE, CA)
        # IMPORTANT - the ack for this okay start pkt will be the first chunk of the file!
        #init window
        wleft = 1
        wright = 5
        #init recv_acks
        recvd = []
        chunks_recvd = {}
        for i in range(1,num+2):
            recvd.append(0)
        while num != 0: # while there are packets left
            if str(wleft) in chunks_recvd:
                tmp = BigSAgain.write(chunks_recvd[str(wleft)])
                del chunks_recvd[str(wleft)]
                wleft+=1
                wright+=1
                num=num-1
                continue
            ServerData, serverAddr = recvreply()
            #if you have recvd an empty chunk or corrupt packet then handle
            if ServerData['header']=="empty":
                continue
            # if it is not a type 4 packet that means client is waiting for ack of num of packets msg
            if ServerData['opcode']!=4:
                msg = "ACK start"
                message = buildPacket(msg, 1, 1, fname)
                MESSAGE = pickle.dumps(message)
                s.sendto(MESSAGE, CA)
                continue
            
            msg_orig = ServerData['DataBody']
            ack_num = ServerData['SeqNo']
            ack_num = int(ack_num)
            old_val = recvd[ack_num]
            recvd[ack_num]=1
            # send ACK
            msg = "this is an ack packet"
            message = buildPacket(msg, 3, ack_num, fname)
            MESSAGE = pickle.dumps(message)
            s.sendto(MESSAGE, CA)
            if old_val==1:
                continue
            if ack_num==wleft:
                # shift window
                wleft = wleft+1
                wright = wright+1
                # write to file
                dataS = BigSAgain.write(msg_orig)
                num = num - 1
                print("Received in order packet number:" + str(ack_num))
            else:
                chunks_recvd[str(ack_num)] = msg_orig
                print("Received out of order packet number:" + str(ack_num))
            
        BigSAgain.close()
        print("New file closed. Check contents in your directory.")

def Download(fname,CA):
    msg = "found"
    message = buildPacket(msg, 1, 1, fname)
    MESSAGE = pickle.dumps(message)
    s.sendto(MESSAGE, CA)
    file = open(fname,"rb")
    size = os.stat(fname)
    sizeS = size.st_size
    print("File size in bytes: " + str(sizeS))
    Num = int(sizeS/256)
    Num = Num + 1
    print("Number of packets to be sent: " + str(Num))
    till = str(Num)
    # buildPacket
    message = buildPacket(till, 1, 1, fname)
    MESSAGE = pickle.dumps(message)
    s.sendto(MESSAGE, CA)
    file = open(fname,"rb")
    #init ack dictionary
    num = Num
    total = Num
    acks=[]
    for i in range(1,num+2):
        acks.append(0)
    chunk_list={}
    for i in range(1,6):
        cur_chunk=file.read(256)
        chunk_list[str(i)]=cur_chunk
    timeout = 15.0
    time_list={}
    wleft=1
    wright=5
    #current packet number
    start_time = time.time()
    pkt_num = 1
    while num!=0:
        #enter if buffer send is complete but first packet not yet acked so window cant shift
        for pnum in range(wleft,pkt_num):
            cur_time = time.time()
            if str(pnum) in time_list:
                if cur_time-time_list[str(pnum)]>=timeout: # retransmit
                    cur_chunk = chunk_list[str(pnum)]
                    if pnum<=total:
                        time_list[str(pnum)] = time.time() # record time
                        message = buildPacket(cur_chunk, 4, pnum, fname)
                        MESSAGE = pickle.dumps(message)
                        s.sendto(MESSAGE, (host, port))
                    print("Retransmitting because of timeout : packet number :" + str(pnum))
        if pkt_num>wright:
            print("Inside if for pktnum and wright = "+str(pkt_num)+","+str(wright)+" ")
            # TO-DO check if any ack has timed out, if so then retransmit
            ServerData,addr = recvreply()
            opcode = ServerData['opcode']
            if opcode==3:
                ack_num = ServerData['SeqNo']
                ack_num = int(ack_num)
                print("Inside if for opcode 3 with pktnum and acknum = "+str(pkt_num)+","+str(ack_num)+" ")
                acks[ack_num] = 1
                if ack_num == wleft: # first packet of buffer in order ack
                    print("Inside if for least ack num with acknum and wleft = "+str(ack_num)+","+str(wleft)+" ")
                    if ack_num==total:
                        break
                    #move window and decrease rem packets
                    num = num - 1
                    wleft = wleft+1
                    wright = wright+1
                    # remove chunk from buffer
                    del chunk_list[str(ack_num)]
                    # add chunk
                    cur_chunk = file.read(256)
                    chunk_list[str(pkt_num)] = cur_chunk
                elif ack_num <wleft: # out of order ack
                    print("Inside elif for ack<wleft with acknum and wleft = "+str(ack_num)+","+str(wleft)+" ")
                else: #in order ack
                    print("Inside else for ack bw wleft,right with acknum and wright = "+str(ack_num)+","+str(wright)+" ")
                    # remove chunk from buffer
                    del chunk_list[str(ack_num)]
            elif opcode==0: # this may not be required. This is basically retransmitting if ERROR packet received but it is difficult to match seq numbers
                msg_recv = ServerData['DataBody']
                msgs = msg_recv.split()
                if msgs[0]=="resend":
                    cur_chunk = chunk_list[msgs[1]] # it probably will not be deleted since ack ni hua abhi
                    message = buildPacket(cur_chunk, 4, msgs[1], fname)
                    MESSAGE = pickle.dumps(message)
                    s.sendto(MESSAGE, CA)
            else: # wait for acks or retransmit timer to end
                print("continuing case waiting for acks or timeout")
        else: #send from buffer - current 256 bytes or less
            cur_chunk = chunk_list[str(pkt_num)]
            # buildPacket
            if pkt_num<=total:
                time_list[str(pkt_num)] = time.time() # record time
                message = buildPacket(cur_chunk, 4, pkt_num, fname)
                MESSAGE = pickle.dumps(message)
                s.sendto(MESSAGE, CA)
            print("Packet number:" + str(pkt_num))
            #next pkt in buffer
            pkt_num = pkt_num + 1
    print("File upload complete")
    end_time = time.time()
    print("time taken : "+str(end_time-start_time))

while True:
    #handshake()
    addr = ()
    while True:
        fname = '' 
        text_full,addr = recvreply()
        if text_full['header']=="empty":
            continue
        tmp = text_full['DataBody'].split()
        if tmp[0]!="hello":
            continue
        text = text_full['DataBody']
        print(text)
        print(addr)
        print("start shake")
        msg = "ACK hello"
        break
    t2 = []
    while True:
        message = buildPacket(msg, 1, 1, fname)
        MESSAGE = pickle.dumps(message)
        s.sendto(MESSAGE, addr)
        print("Message Sent to Client.")
        text_full,addr_temp = recvreply()
        if text_full['header']=="empty":
            continue
        text = text_full['DataBody']
        t2 = text.split()
        if t2[0]=="upload" or t2[0]=="download":
            try:
                print("data print: "+" "+t2[0]+" "+t2[1])
            except:
                print("wrong receival hence retry")
                continue
            break
        else:
            continue
    # recvd upload/download request ka ACK. now this may get lost but we will handle during upload/download
    msg = "ACK updown"
    message = buildPacket(msg, 1, 1, fname)
    MESSAGE = pickle.dumps(message)
    s.sendto(MESSAGE, addr)
    # IMPORTANT - The ACK for upload/download is actually number of packets 
    if t2[0] == "download":
        if os.path.isfile(t2[1]):
            print("Go to download func")
            Download(t2[1],addr)
        else:
            msg = "Not found"
            message = buildPacket(msg, 1, 1, fname)
            MESSAGE = pickle.dumps(message)
            s.sendto(MESSAGE, addr)
    elif t2[0] == "hello":
        print("Go to handshake func")
        handshake(t2)
    elif t2[0] == "upload":
        print("Go to upload func")
        Upload(t2,addr)
    elif t2[0] == "list":
        print("Go to list func")
        ServerList()
    elif t2[0] == "exit":
        print("End connection")
        ServerExit()
    else:
        InvalidRequest(t2)

print("Program will end now. ")
quit()