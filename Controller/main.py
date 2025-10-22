import tkinter as tk
from tkinter import ttk
import sv_ttk as sv

connection = 0

def sendshape(shape):
    if connection == 0:
        print('No Connection')
        return
    usr = input('Warning! Only send drone path commands when drone is stationary. Confirm that drone is stationary Y/N:')
    if usr == 'N':
        return
    elif usr == 'Y':
        if shape == 1:
            print('circle')
        elif shape == 2:
            print('hexagon')
        elif shape == 3:
            print('figure 8')
    else:
        return
    
def connect(address):
    global connection
    add = '109.106.1.1'
    if address == add:
        print('Connected')
        connection = 1
    
    
def disconnect():
    return

def land():
    return

def mainwindow():
    #init
    root = tk.Tk()
    sv.set_theme("dark")
    root.title("Drone Controller")
    root.geometry('800x300')
    
    #textbox and label
    connectionframe = ttk.LabelFrame(root, text='Drone Communication', padding=10)
    connectionframe.pack(fill = 'x', padx=10,pady=5)
    
    ttk.Label(connectionframe, text='Connection Address:').pack(side='left')
    ip_entry = ttk.Entry(connectionframe)
    ip_entry.pack(side='left', padx=5)
    ttk.Button(connectionframe, text='Connect', command=lambda: connect(ip_entry.get())).pack(side='left')
    ttk.Button(connectionframe, text='Disconnect', command=disconnect).pack(side='right', padx=5)
    ttk.Button(connectionframe, text='Manual Override', command=lambda: land).pack(side='right')

    #flight paths
    flight_frame = ttk.LabelFrame(root, text="Flight Paths", padding=10)
    flight_frame.pack(fill="both", expand=True, padx=10, pady=5)
    
    ttk.Button(flight_frame, text='Circle',
               command=lambda:sendshape(1)).pack(pady=5)
    ttk.Button(flight_frame, text='Hexagon',
               command=lambda:sendshape(2)).pack(pady=5)
    ttk.Button(flight_frame, text='Figure 8',
               command=lambda:sendshape(3)).pack(pady=5)
    
    
    
    root.mainloop()
    





if __name__ == "__main__":
    mainwindow()
