# SocialTorrent

Social torrent script. The script acts as both the client and/or the server.

When the script is started, it will act as a server as long as no input is given. If you want to act as a client and hook up to servers to download files, you should type in "connect [ip_adress]" to connect to the ip adress (assuming the ports are same).

When a server, the script transfers files to clients who are connected to it. It will continue to run until script is closed or until the user writes "-close".

When a client and connected to a server, it will ask you which files to download from it. Each server will send the file names & sizes in the directory which the script is ran. After that the user writes a new name for the requested file. When the file download is finished, the script terminates.

WARNING: if you enter an input after starting the script, you cannot write anymore inputs (not when written "connect [ip_adress]" with a correct ip adress, then the program will ask you for file infos). You need to run the script again.

# Usage

Program:

     python torrent.py [PORT]

#  Test

Tested on Windows 10, with Python 3.7.4

# example: 

python torrent.py 12345

connect [192.168.1.2]
