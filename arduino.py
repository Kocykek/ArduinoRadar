import serial
import threading
import time
import tkinter as tk
from tkinter import ttk
import math
import os
import csv
import mysql.connector
from datetime import datetime

def insert_data(kat, odleglosc):
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",  # replace if different
            password="newpassword",  # replace with your password
            database="arduino"
        )

        cursor = connection.cursor()

        sql = "INSERT INTO Rekordy (kat, odleglosc, kiedy) VALUES (%s, %s, %s)"
        data = (kat, odleglosc, datetime.now())

        cursor.execute(sql, data)
        connection.commit()

        print("✅ Data inserted into MySQL.")

    except mysql.connector.Error as err:
        print(f"❌ MySQL Error: {err}")

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

if not os.path.exists("collected_data.csv") or os.path.getsize("collected_data.csv") == 0:
    with open("collected_data.csv", mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(["Kąt", "Odległość", "Kiedy?"])


def save_to_csv(filename, data):
    # data is a list of tuples/lists: (angle, distance, timestamp)
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file, delimiter=';')
        writer.writerow(['Angle', 'Distance', 'Timestamp'])  # header
        for row in data:
            writer.writerow(row)


class ServoController:
    def __init__(self, port='/dev/ttyUSB0', baudrate=9600, update_distance_callback=None):
        self.arduino = serial.Serial(port=port, baudrate=baudrate, timeout=1)
        self.running = False
        self.thread = None
        self.read_thread = None
        self.update_distance_callback = update_distance_callback
        self.last_position = None
        self.reading = True

    def move_servo(self, angle):
        if 10 <= angle <= 170:
            self.arduino.write(f"{angle}\n".encode())
            self.last_position = angle
            print(f"Manually sent angle: {angle}")
    def send_command(self, cmd):
        if self.arduino.is_open:
            cmd_to_send = cmd.strip() + '\n'  # make sure it ends with newline
            self.arduino.write(cmd_to_send.encode('utf-8'))

    def start_sweep(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self.sweep_loop)
        self.thread.start()

    def stop_sweep(self):
        self.running = False
        if self.thread:
            self.thread.join()
            self.thread = None

    def sweep_loop(self):
        positions = list(range(10, 171, 1)) + list(range(170, 9, -1))
        while self.running:
            for pos in positions:
                if not self.running:
                    break
                cmd = f"{pos}\n"
                self.arduino.write(cmd.encode())
                self.last_position = pos
                print(f"Sent: {pos}")
                time.sleep(0.05)

    def start_reading(self):
        self.reading = True
        self.read_thread = threading.Thread(target=self.read_serial)
        self.read_thread.start()

    def stop_reading(self):
        self.reading = False
        if self.read_thread:
            self.read_thread.join()
            self.read_thread = None

    def read_serial(self):
        while self.reading:
            try:
                line = self.arduino.readline().decode('utf-8').strip()
                if line and "Distance:" in line:
                    if self.update_distance_callback:
                        self.update_distance_callback(line)
            except Exception as e:
                print(f"Error reading serial: {e}")

    def close(self):
        self.stop_sweep()
        self.stop_reading()
        self.arduino.close()

class RadarCanvas(tk.Canvas):
    def __init__(self, parent, width=300, height=300, max_distance=200, **kwargs):
        super().__init__(parent, width=width, height=height, bg='black', **kwargs)
        self.width = width
        self.height = height
        self.center_x = width // 2
        self.center_y = height // 2
        self.max_distance = max_distance  # max distance in cm for scaling
        self.points = {}  # dictionary to store latest distance by angle
        self.current_angle = None  # <-- add this
        self.create_oval(10, 10, width-10, height-10, outline='green')  # Outer circle
        # Draw concentric circles for range markers
        for r in range(1, 5):
            radius = (width//2 - 10) * r / 5
            self.create_oval(self.center_x - radius, self.center_y - radius,
                             self.center_x + radius, self.center_y + radius,
                             outline='darkgreen', dash=(2, 4))

        # Draw center cross
        self.create_line(self.center_x, 10, self.center_x, height-10, fill='darkgreen')
        self.create_line(10, self.center_y, width-10, self.center_y, fill='darkgreen')

    def update_point(self, angle, distance):
        # Store the latest distance for the given angle
        self.points[angle] = (distance, time.time())
        self.redraw()

    def set_current_angle(self, angle):
        self.current_angle = angle
        self.redraw()

    def on_slider_change(value):
        angle = int(float(value))
        move_servo(angle)  # Your function to control the servo

    
    def redraw(self):
    # Clear previous dots (points + sweep line)
        self.delete("dots")

        current_time = time.time()
        to_delete = []

        # Draw all points first
        for angle, (distance, timestamp) in self.points.items():
            if current_time - timestamp > 2:
                to_delete.append(angle)
                continue
            if distance <= 0 or distance > self.max_distance:
                continue  # Ignore invalid or out of range

            # Calculate radius for distance scaling
            scale_factor = 2.5
            radius = (distance / self.max_distance) * (self.width//2 - 15) * scale_factor

            radar_angle_deg = 180 - angle
            radar_angle_rad = math.radians(radar_angle_deg)

            x = self.center_x - radius * math.cos(radar_angle_rad)
            y = self.center_y - radius * math.sin(radar_angle_rad)

            # Draw the point
            if distance <= 10:
                color = 'red'
            elif distance <= 30:
                color = 'yellow'
            else:
                color = 'lime'
            self.create_oval(x-4, y-4, x+4, y+4, fill=color, outline='', tags="dots")

        # Remove old points
        for angle in to_delete:
            del self.points[angle]

        # Draw the radar sweep line once, *after* drawing all points
        if self.current_angle is not None:
            radar_angle_deg = 180 - self.current_angle
            radar_angle_rad = math.radians(radar_angle_deg)
            length = self.width // 2 - 10  # length of the line to edge of radar circle

            x_end = self.center_x - length * math.cos(radar_angle_rad)
            y_end = self.center_y - length * math.sin(radar_angle_rad)

            self.create_line(self.center_x, self.center_y, x_end, y_end, fill='lightblue', width=2, tags="dots")



class App(tk.Tk):
    

    def __init__(self):
        self.collected_data = [] 
        super().__init__()
        self.title("Servo Controller + Radar Display")
        self.geometry("400x500")

        self.status_label = ttk.Label(self, text="Waiting for data...", font=("Arial", 14))
        self.status_label.pack(pady=10)

        self.radar = RadarCanvas(self, width=350, height=350, max_distance=200)
        self.radar.pack(pady=10)

        self.controller = ServoController(update_distance_callback=self.update_status)

        self.start_btn = ttk.Button(self, text="Start Sweep", command=self.start_sweep)
        self.start_btn.pack(pady=5)

        self.stop_btn = ttk.Button(self, text="Stop Sweep", command=self.stop_sweep)
        self.stop_btn.pack(pady=5)

        self.angle_slider = tk.Scale(self, from_=10, to=170, orient=tk.HORIZONTAL,
                             label="Manual Servo Control", command=self.slider_changed)
        self.angle_slider.pack(pady=10)

        self.buzzer_var = tk.BooleanVar(value=False)
        self.buzzer_check = ttk.Checkbutton(self, text="Enable Buzzer", variable=self.buzzer_var,
                                            command=self.buzzer_toggled)
        self.buzzer_check.pack(pady=10)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.controller.start_reading()

        self.save_to_csv_var = tk.BooleanVar()
        self.checkbox = tk.Checkbutton(self, text="Save every 2nd data to CSV", variable=self.save_to_csv_var)
        self.checkbox.pack()



    def save_csv(self):
        if self.collected_data:
            save_to_csv("radar_data.csv", self.collected_data)
            print("Data saved to radar_data.csv")
        else:
            print("No data to save.")

    def slider_changed(self, value):
        angle = 180 - int(float(value))
        self.controller.move_servo(angle)

    def start_sweep(self):
        self.controller.start_sweep()

    def stop_sweep(self):
        self.controller.stop_sweep()

    def buzzer_toggled(self):
        if self.buzzer_var.get():
            self.controller.send_command("TURN_BUZZER_ON")
        else:
            self.controller.send_command("TURN_BUZZER_OFF")

    def update_status(self, distance_text):
        # Example input: "Distance: 123 cm"
        try:
            parts = distance_text.split()
            distance = int(parts[1])
            servo_pos = self.controller.last_position

            # Update text label
            text = f"{distance_text}\nServo angle: {servo_pos if servo_pos is not None else 'N/A'}°"
            self.after(0, self.status_label.config, {"text": text})

            # Update radar if we have servo angle
            if servo_pos is not None:
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())  # human-readable timestamp
                data_point = (servo_pos, distance, timestamp)
                
                self.collected_data.append((servo_pos, distance, timestamp))
                if self.save_to_csv_var.get() and len(self.collected_data) % 2 == 0:
                    with open("collected_data.csv", mode="a", newline="") as file:
                        writer = csv.writer(file, delimiter=";")
                        writer.writerow(data_point)
                        insert_data(servo_pos, distance)


                self.radar.update_point(servo_pos, distance)
                self.radar.set_current_angle(servo_pos)  # <-- add this line
        except Exception as e:
            print(f"Failed to update status: {e}")

    def on_closing(self):
        self.controller.close()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()
