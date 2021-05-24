import tkinter as tk
from client import sender
from tkinter.filedialog import askdirectory
from PIL import Image, ImageTk
import time
import os 
import sys

directory = ""
upload = 0
# GUI
HEIGHT = 600
WIDTH = 600

def upload():
	global directory
	print("upload begin")
	s1 = sender(directory)
	s1.send()

def download():
	print("download begin")

def upload_inp(dir):
    global directory
    directory = dir
    print(directory)
    while True: 
        if directory == '9':
            label['text'] = "Exited."
            root.destroy()
            return
        elif os.path.isfile(directory):
            label['text'] = f"Uploading {directory}. Please wait."
            break
        else :
            label['text'] = "Wrong directory. Please check or Press 9 to exit."
            return
    print(dir)
    print("upload begin")
    start_time = time.time()
    s1 = sender(directory)
    s1.send()
    print("Time taken = " + str(start_time-time.time()))
    
def download_inp(dir):
    # label['text'] = f "Your query is {query}."
    global directory
    directory = dir
    print(directory)
    while True: 
        if directory == '9':
            label['text'] = "Exited."
            root.destroy()
            return
        else :
            label['text'] = f"Downloading {directory}. Please wait."
            break
    print(dir)
    print("Download begin")
    start_time = time.time()
    s1 = sender(directory)
    s1.recv()
    print("Time taken = " + str(start_time-time.time()))

root = tk.Tk()
canvas = tk.Canvas(root, height=HEIGHT, width=WIDTH)
canvas.pack()

imagex = Image.open('background.jpg')
photo = ImageTk.PhotoImage(imagex,master=root)
background_label = tk.Label(root, image=photo)
background_label.image = photo
background_label.place(relwidth=1, relheight=1)

frame = tk.Frame(root, bg='#C0C0C0', bd=5)
frame.place(relx=0.5, rely=0.1, relwidth=0.85, relheight=0.085, anchor='n')

entry = tk.Entry(frame, font=40)
entry.place(relwidth=0.55, relheight=0.8)

button = tk.Button(frame, text="File to upload", font=30, command=lambda: upload_inp(entry.get()))
button.place(relx=0.6, relheight=0.8, relwidth=0.4)

frame2 = tk.Frame(root, bg='#C0C0C0', bd=5)
frame2.place(relx=0.5, rely=0.3, relwidth=0.85, relheight=0.085, anchor='n') 

entry2 = tk.Entry(frame2, font=40)
entry2.place(relwidth=0.55, relheight=0.8)

button2 = tk.Button(frame2, text="File to download", font=30, command=lambda: download_inp(entry2.get()))
button2.place(relx=0.6, relheight=0.8, relwidth=0.4)

lower_frame = tk.Frame(root, bg='#4F2412', bd=10)
lower_frame.place(relx=0.5, rely=0.45, relwidth=0.85, relheight=0.5, anchor='n')

label = tk.Label(lower_frame)
label.place(relwidth=1, relheight=1)

root.mainloop()
