import time
import os 
import sys
import socket
import math
import hashlib
import pickle

#calculate seq num
# if pkt_num<11:
# 	seq_num = pkt_num-1
# elif pktnum%10!=0:
# 	seq_num = (pkt_num%10)-1 # pkt 11 = 0 12 = 1...19 = 8 20 = 9 ; 21 = 0 
# else:
# 	seq_num = 9

#helper
def megabytes_to_bytes(mb):
    return mb * 1024 * 1024

#return packet
def buildPacket(msg,opcode,seq_num,fname):
    print("start packet build")
    #Creating Header
    header = {}
    header['port_s'] = 420
    header['port_d'] = 5000
    header['length'] = len(msg)
    #creating Checksum
    #if type(msg) is bytes:
        #msg = msg.decode() 
    checksum = '' + str(len(msg))  + str(header['port_s']) + str(header['port_d'])
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


#receive ack/reply from server and return
def recvreply(s):
	recvd = False
	try:
	    ClientData_flat, clientAddr = s.recvfrom(4096)
	    ClientData = pickle.loads(ClientData_flat)
	    recvd = True
	except ConnectionResetError:
	    print("Error. Port numbers not matching. Exiting. Next time enter same port numbers.")
	except:
	    print("Timeout or some other error")
	#text = ClientData['DataBody'].decode('utf8')
	if recvd:
		text = ClientData
		return text,clientAddr
	else:
		emsg = {}
		emsg['header']="empty"
		return emsg,"error"

def downloading(s,host,port,fname):
    # start receiving
    print("In Client, download function")
    saveloc = "./downloads_client/"+fname
    BigSAgain = open(saveloc, "wb")
    d = 0
    print("Receiving number of packets first.")
    Count_full, countaddress = recvreply(s) # num packets
    Count = Count_full['DataBody']
    print(Count)
    num = int(Count)
    print("Num of packets "+Count)
    print("Receiving packets will start now if file exists.")
    #init window
    wleft = 1
    wright = 5
    #init recv_acks
    recvd = []
    for i in range(1,num+2):
        recvd.append(0)
    while num != 0: # while there are packets left
        ServerData, serverAddr = recvreply(s)
        msg_orig = ServerData['DataBody']
        ack_num = ServerData['SeqNo']
        ack_num = int(ack_num)
        recvd[ack_num]=1
        # send ACK
        msg = "this is an ack packet"
        message = buildPacket(msg, 3, ack_num, fname)
        MESSAGE = pickle.dumps(message)
        s.sendto(MESSAGE, (host,port))
        if ack_num==wleft:
            # shift window
            wleft = wleft+1
            wright = wright+1
            # write to file
            dataS = BigSAgain.write(msg_orig)
            num = num - 1
            print("Received in order packet number:" + str(ack_num))
        else:
            print("Received out of order packet number:" + str(ack_num))
        
    BigSAgain.close()
    print("New file closed. Check contents in your directory.")

def uploading(s,host,port,fname,num):
	file = open(fname,"rb")
	#init ack dictionary
	total = num
	acks=[]
	for i in range(1,num+2):
		acks.append(0)
	chunk_list={}
	for i in range(1,6):
		cur_chunk=file.read(256)
		chunk_list[str(i)]=cur_chunk
	# timer for timeouts
	timeout = 15.0
	time_list={}
	wleft=1
	wright=5
	#current packet number
	start_time = time.time()
	pkt_num = 1
	while num != 0:
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
			#next pkt in buffer

		if pkt_num>wright:
			print("Inside if for pktnum and wright = "+str(pkt_num)+","+str(wright)+" ")
			# TO-DO check if any ack has timed out, if so then retransmit
			ServerData,addr = recvreply(s)
			if ServerData['header']=="empty":
				continue
			else:
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
						#del chunk_list[str(ack_num)]
						# add chunk
						cur_chunk = file.read(256)
						chunk_list[str(pkt_num)] = cur_chunk
					elif ack_num <wleft: # out of order ack
						print("Inside elif for ack<wleft with acknum and wleft = "+str(ack_num)+","+str(wleft)+" ")
					else: #in order ack
						print("Inside else for ack bw wleft,right with acknum and wright = "+str(ack_num)+","+str(wright)+" ")
						# remove chunk from buffer
						#del chunk_list[str(ack_num)]
				elif opcode==0: # this may not be required. This is basically retransmitting if ERROR packet received but it is difficult to match seq numbers
					msg_recv = ServerData['DataBody']
					msgs = msg_recv.split()
					if msgs[0]=="resend":
						cur_chunk = chunk_list[msgs[1]] # it probably will not be deleted since ack ni hua abhi
						message = buildPacket(cur_chunk, 4, msgs[1], fname)
						MESSAGE = pickle.dumps(message)
						s.sendto(MESSAGE, (host, port))
				else: # wait for acks or retransmit timer to end
					print("continuing case waiting for acks or timeout")
		else: #send from buffer - current 256 bytes or less
			cur_chunk = chunk_list[str(pkt_num)]
			# buildPacket
			if pkt_num<=total:
				time_list[str(pkt_num)] = time.time() # record time
				message = buildPacket(cur_chunk, 4, pkt_num, fname)
				MESSAGE = pickle.dumps(message)
				s.sendto(MESSAGE, (host, port))
			print("Packet number:" + str(pkt_num))
			#next pkt in buffer
			pkt_num = pkt_num + 1
	print("File upload complete")
	end_time = time.time()
	print("subtraction : " + str(time.time()-15))
	print("time taken : "+str(end_time-start_time))
	# if end_time-start_time>2.0:
	# 	print("More than 2")

#three way shaker
def twhs(s,host,port,fname):
    print("inside twhs")
    msg = "hello connect"
    # build conn estab packet
    while True:
	    message = buildPacket(msg, 5, 5, fname)
	    MESSAGE = pickle.dumps(message)
	    s.sendto(MESSAGE, (host, port))
	    full_text, clientAddr = recvreply(s)
	    if full_text['header']=="empty":
	    	continue
	    else:
		    text = full_text['DataBody']
		    print("first reply from twhs"+" "+text)
		    rep_split = text.split()
		    if rep_split[0]!="okay":
		        continue
		    else:
		    	break
    while True:
	    msg = "upload"+" "+fname
	    message = buildPacket(msg, 1, 1, fname)
	    MESSAGE = pickle.dumps(message)
	    s.sendto(MESSAGE, (host, port))
	    full_text, clientAddr = recvreply(s)
	    if full_text['header']=="empty":
	    	continue
	    else:
		    text = full_text['DataBody']
		    print("reply from twhs"+" "+text)
		    rep_split = text.split()
		    if rep_split[0]!="okay":
		        continue
		    else:
		    	break # upload ack recvd
    return True	    	

def twhs_download(s,host,port,fname):
    print("inside twhs")
    msg = "hello connect"
    # build conn estab packet
    message = buildPacket(msg, 5, 5, fname)
    MESSAGE = pickle.dumps(message)
    s.sendto(MESSAGE, (host, port))
    full_text, clientAddr = recvreply(s)
    text = full_text['DataBody']
    print("first reply from twhs"+" "+text)
    rep_split = text.split()
    if rep_split[0]=='denied':
        return False
    msg =  "download "+ " " +fname
    # build download request packet
    message = buildPacket(msg, 1, 1, fname)
    MESSAGE = pickle.dumps(message)
    s.sendto(MESSAGE, (host, port))
    full_text, clientAddr = recvreply(s)
    text = full_text['DataBody']
    rep_split = text.split()
    if rep_split[0]=='Not': # file not on server
    	return False
    return True
    
class sender:
    fname = ''
    s = ""
    host = ''
    port = 0
    def __init__(self,file):
        self.fname = file
        self.host = '127.0.0.1'
        self.port = 5000
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            print("Client socket initialized")
            self.s.setblocking(0)
            self.s.settimeout(5)
        except socket.error:
            print("Failed to create socket")
            sys.exit()
    
    def send(self):
        ## 3 way handshake
        host = self.host
        port = self.port
        s = self.s
        fname = self.fname
        shake = twhs(s,host,port,fname)
        if shake==False:
            sys.exit()
        ## handshake hogaya successfull
        print("Now we shall start sending data.")
        ## send data
        size = os.stat(fname)
        sizeS = size.st_size
        #print("File size in bytes: " + str(sizeS))
        Num = int(sizeS/256)
        Num = Num + 1
        print("Number of packets to be sent: "+str(Num))
        # buildPacket
        while True:
        	message = buildPacket(str(Num), 1, 1, fname)
        	MESSAGE = pickle.dumps(message)
        	s.sendto(MESSAGE, (host, port))
        	full_text, clientAddr = recvreply(s)
        	if full_text['header']=="empty":
        		continue
        	else:
        		text = full_text['DataBody']
        		print("first reply from twhs"+" "+text)
        		rep_split = text.split()
        		if rep_split[0]!="okay":
        			continue
        		else: # we start file upload
        			break
        uploading(s,host,port,fname,Num)

    def recv(self):
        host = self.host
        port = self.port
        s = self.s
        fname = self.fname
        shake = twhs_download(s,host,port,fname)
        if shake==False:
        	sys.exit()
        print("Now we shall start downloading data")
        downloading(s,host,port,fname)


fname = 'apples.jpg'
#fname = './hey.txt'
#fname = 'one.pdf'
#fname = './video.mp4'
#fname = './largepdf.pdf'
#fname = './movie.mkv'
s1 = sender(fname)
s1.send()
