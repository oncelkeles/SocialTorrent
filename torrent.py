import socket
import ipaddress
import sys
import select
import threading
import queue
import time
import os
from threading import Thread



# global inits
bufferSIZE = 1500
ip  = socket.gethostbyname(socket.gethostname())
HOST = ip
PORT = int(sys.argv[1])

PACKET_COUNTS = []

COUNT = -1
TRANSFER_FILE_NAME = []
TRANSFER_PACKET_NUMBER = []

chunks_of_file = []
download_name = "" 

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))

# gets user input at the start
def UserInput():
	print("Write \'connect [ip_adress]\' to connect to a server as a client. Don't write anything to act as a server.")
	user_input = input()
	if user_input[0:7] == "connect":
		try:
			index_start = user_input.find('[')
			index_end = user_input.find(']')
			server = user_input[index_start+1:index_end]
			print("Connected to : - " + server +" -")
			user_input  = user_input.encode('latin1')
			s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			s.sendto(user_input,(server, PORT))
			s.close()

		except:
			print("err")
	elif user_input == "-close":
		exit()

# search for other servers in network to download file from them also
def SearchOthers(file_name, size):
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	file_input = "DOWNLOAD " + file_name
	file_input = file_input.encode('latin1')
	s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST,1)
	for x in range(3):
		s.sendto( file_input, ('<broadcast>', PORT))
	s.close()

	
	

# file transfer function
def Transfer(conn_ip, file_name):
	global TRANSFER_FILE_NAME
	global TRANSFER_PACKET_NUMBER
	global PACKET_COUNTS
	global COUNT

	transferring = 1

	COUNT += 1
	temp = COUNT

	TRANSFER_FILE_NAME.append(0) 
	TRANSFER_PACKET_NUMBER.append(0)

	# open file, initialize necessary connections
	my_file = open(file_name, "rb")
	byte_buffer = my_file.read()
	byte_len = len(byte_buffer)
	number_of_packets = byte_len / (bufferSIZE-50)
	if(byte_len % (bufferSIZE-50)):
		number_of_packets = int(number_of_packets) + 1
	count = -1
	my_file.close()
	print("Number of packets: " + str(number_of_packets))

	# check if file transfer should start
	msg = "Sending File:  [" + file_name + "]" + "#" + str(temp)
	msg = msg.encode('latin1')

	while (count == -1):
		try:
			sock.sendto(msg, (conn_ip, PORT))
			
			
			if TRANSFER_FILE_NAME[temp] == 1:
				count += 1
				print("File name sent.")
				
		except:
			print("Couldn't send file name")
		time.sleep(1)

	# send number of packets in order to ack and track the transfer
	msg = "Number of Packets: [" + str(number_of_packets) + "]" + "#" + str(temp)
	msg = msg.encode('latin1')
	while (count == 0):
		try:
			sock.sendto(msg, (conn_ip, PORT))

			if TRANSFER_PACKET_NUMBER[temp] == 1:
				count += 1
				print("Packet numbers sent.")
		except:
			print("Couldn't send packet number")
		time.sleep(1)

	i = 0
	file_chunks = []
	file_chunks_sent = []

	# dividing file into chunks to be sent packet by packet
	# giving sequence number in front of the packets in order to track (10 digits)
	my_file2 = open(file_name, "rb")
	seq_num_digits = 10 - len(str(number_of_packets))
	while(i < number_of_packets):
		temp = ""
		seq_num_digits = 10 - len(str(i))
		for y in range(seq_num_digits):
			temp = temp + "0"
		temp = temp + str(i)
		temp2 = my_file2.read(bufferSIZE-50)
		#print("Original Data SIZE := " + str(sys.getsizeof(temp2)))
		temp2 = temp2.decode('latin1')
		temp = temp + temp2
		temp = str.encode(temp, 'latin1')
		file_chunks.append(temp)
		file_chunks_sent.append(0)
		
		i += 1
	my_file2.close()
	

	i = 0
	my_file2 = open(file_name, "rb")
	# transferring file by chunks, sends all unacked packets, wait for 1 sec then repeats until all packets are acked
	while(transferring == 1):
		for seq in range(number_of_packets):
			if file_chunks_sent[seq] == 0:
				data = file_chunks[seq]
				sock.sendto(data,(conn_ip, PORT))	
				print("Packet #" + str(seq) + " is BEING SENT NOW, size is = " + str(sys.getsizeof(data)))
			else:
				print("#" + str(seq) + " is already SENT")
		time.sleep(1)
		for x in range(len(PACKET_COUNTS)):
			temp = PACKET_COUNTS.pop()
			file_chunks_sent[temp] = 1

		check_finish = 1
		count = 0
		while(count < number_of_packets):
			if(file_chunks_sent[count] == 0):
				check_finish = 0
			count += 1

		if check_finish == 1:
			transferring = 0	

	# below checks if all packets are sent, if so, end transfer
	if transferring == 0:
		for seq in range(number_of_packets):


			if file_chunks_sent[seq] == 0:
				data = file_chunks[seq]
				sock.sendto(data,(conn_ip, PORT))	
			else:
				a = 0
		for x in range(len(PACKET_COUNTS)):
			temp = PACKET_COUNTS.pop()
			file_chunks_sent[temp] = 1

	print("File Sent!")

# merges received file after transfer with the right order
def MergeFile():
	if download_name != "":
		print ('Merging file data...')
		size = 0
		new_file = open(download_name, 'wb')
		for x in range(len(chunks_of_file)):
			data = chunks_of_file[x]
			size = size + sys.getsizeof(data)
			new_file.write(data)
		print("Merge done!")
		exit()

# listen to incoming packets
def UDPListen():

	global TRANSFER_FILE_NAME
	global TRANSFER_PACKET_NUMBER
	global PACKET_COUNTS
	global COUNT
	global new_file
	global chunks_of_file
	global download_name

	got_packet_number = 0
	packet_number_count = 0
	packet_number = ""
	counting = 0


	while True:
		data, addr = sock.recvfrom(bufferSIZE)
		if data and addr[0] != HOST:
			data_stream = data
			data = data.decode('latin1')

			# discover message handling
			if data[0:8] == "DISCOVER":
				print(data[0:])
				msg = "I'm here too: " + HOST
				msg = msg.encode('latin1')
				s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
				s.sendto(msg, (addr[0], PORT))
				s.close()

			# handles discover response
			elif data[0:12] == "I'm here too":
				print(data)	

			# if some other server tries to connect
			elif data[0:7] == "connect":
				index_start = data.find('[')
				index_end = data.find(']')
				conn_ip = data[index_start+1:index_end]
				print("Received connection from " + str(addr[0]))
				files = [f for f in os.listdir('.') if os.path.isfile(f)]
				fs = []
				msg = "AVAILABLE FILES: "
				for f in files:
					fs = str(f)
					size = os.path.getsize(f)
					msg = msg + fs + " - size: "+ str(size) + "bytes, "
				msg = msg.encode('latin1')
				s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
				s.sendto(msg, (addr[0], PORT))
				s.close()

			# lists available files to download from connected server
			elif data[0:15] == "AVAILABLE FILES":
				print()
				print(data)
				print()
				
				# get file name and size
				file_input = input("Write the FULL NAME of the file WITH FORMAT you want to download, e.g. \'image.jpg\': " )
				f = file_input
				index_name = data.find(f)
				index_size_start = index_name + len(f) + 9 
				index_size_end = data.find("b", (index_name + 9))
				size = data[index_size_start:index_size_end]
				size = int(size)
				print("Size: " + str(size))
				file_input = "DOWNLOAD " + file_input
				print()
				# user writes a new name for the file
				download_name = input("Write the NEW name of the file WITHOUT THE FORMAT to be created, e.g. \'my_image\': ") #def te global yapıp son nokta find + append format
				file_format_index = file_input.rfind(".")
				file_format = file_input[file_format_index:]
				
				download_name = download_name + file_format
				SearchOthers(download_name, size)
				print()
				print("DOWNLOADING file "+ f + " as " + download_name + " ...")
				print()
				file_input = file_input.encode('latin1')
				s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
				s.sendto(file_input, (addr[0], PORT))
				s.close()

			# finds requested file from directory and starts file transfer
			elif data[0:8] == "DOWNLOAD":
				file_name = data[9:]
				files = [f for f in os.listdir('.') if os.path.isfile(f)]
				for f in files:
					if f == file_name:
						print("Starting transfer...")
						ThreadTransfer = Thread(target=Transfer, args=(addr[0], file_name, ))
						ThreadTransfer.start()

			# get file name and send ack
			elif data[0:12] == "Sending File":
				index_start = data.find('[')
				index_end = data.find(']')
				num_start = data.find('#')
				temp = data[num_start+1:len(data)]
				file_name = data[index_start+1:index_end]
				try:
					msg = "File Tranfer ACKED " + temp
					msg = msg.encode('latin1')
					s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
					s.sendto(msg, (addr[0], PORT))
					s.close()
				except:
					print("Couldn't ack transfer")

			# file transfer start ack
			elif data[0:18] == "File Tranfer ACKED":
				temp = data[19:len(data)]
				temp = int(temp)
				TRANSFER_FILE_NAME[temp] = 1

			# number of packets received ack
			elif data[0:23] == "Number of Packets ACKED":
				temp = data[24:len(data)]
				temp = int(temp)
				TRANSFER_PACKET_NUMBER[temp] = 1

			# get number of packets and send ack
			elif data[0:17] == "Number of Packets":
				index_start = data.find('[')
				index_end = data.find(']')
				packet_number = data[index_start+1:index_end]
				num_start = data.find('#')
				temp = data[num_start+1:len(data)]

				str_temp = "0"
				str_temp = str_temp.encode('latin1')
				if got_packet_number == 0:
					got_packet_number = 1
					for x in range(int(packet_number)):
						chunks_of_file.append(str_temp)

				msg = "Number of Packets ACKED " + temp
				msg = msg.encode('latin1')
				try:
					s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
					s.sendto(msg, (addr[0], PORT))
					s.close()
				except:
					print("Couldn't ack packet number")

			# get ACK of packet number
			elif data[0:3] == 'ACK':	
				temp_number = int(data[4:(len(data))])
				PACKET_COUNTS.append(temp_number)

			# get file data	
			elif len(data) > 10:
				# get sequence number from beginng of the packet
				seq_number = int(data[0:10])
				msg = "ACK " + str(seq_number)
				msg = msg.encode('latin1')
				check_packet_number = packet_number_count + 1
				check = chunks_of_file[seq_number].decode('latin1')
				# do not handle packets if the packet is already handled
				while(check_packet_number > packet_number_count) :
					s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
					s.sendto(msg, (addr[0], PORT))
					s.close()
					if check != "0":
						check_packet_number -= 1
					else:
						try:
							#s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
							#s.sendto(msg, (addr[0], PORT))
							#s.close()

							data_stream = data[11:]
							data = data.encode('latin1')
							data = data[10:]
							chunks_of_file[seq_number] = data
							packet_number_count +=1
							counting += 1
						except:
							print("Couldn't ack packet")

					if(check_packet_number == (int(packet_number))):
						packet_number_count = 0
						check_packet_number = 0
						data = ""
						MergeFile()


				
def main():
	global HOST
	print("HOST: ")
	print(HOST)
	print("PORT: ")
	print(PORT)
	print()

	# broadcast discover 
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.bind(('', PORT))
	s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST,1)
	for x in range(3):
		msg =("DISCOVER " + HOST + ": I'm here!")
		msg = msg.encode('latin1')
		s.sendto( msg, ('<broadcast>', PORT))
	s.close()   

	ThreadUDPListen = Thread(target=UDPListen)
	ThreadUDPListen.start()

	UserInput()

if __name__ == ("__main__"):
	main()
