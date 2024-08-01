import sys
from PyQt5.QtWidgets import QApplication, QWidget, QCheckBox, QGridLayout, QTextEdit, QPushButton, QVBoxLayout, QLabel, QHBoxLayout, QTableWidget
from PyQt5.QtCore import QTimer
import numpy as np
import random
import time

class MyApp(QWidget):
    def __init__(self):
        super().__init__()

        self.N = 20 + 2
        self.Tc = 10 + 15
        self.l_tc = 1/self.Tc
        self.Ts = 15 + 12
        self.l_ts = 1/self.Ts
        self.Z = 2 # Workers
        self.max_detail = 10

        self.prev_time = 0
        self.current_time = 0
        self.all_dt = []

        self.free_workers = self.Z

        self.speedrun = False

        self.log_str = ""

        self.avr_idle = 0
        self.idle_counts = []
        self.max_idle = 0
        self.max_tuning = 0
        self.avr_tuning = 0
        self.tuning_counts = []
        self.avr_busy_workers = 0
        self.max_busy_workers = 0
        self.busy_workers_counts = []

        self.FEC = [Machine(
        i, r_t(self.l_tc)
                   ) for i in range(1, self.N+1)]
        self.CEC = []

        self.timer_state = "FP"

        self.initUI()

    def initUI(self):

        self.info_label = QLabel(str(self.free_workers), self)

        self.fec_label = QLabel("FEC", self)
        self.fec_text = QTextEdit(self)
        self.fec_text.setPlainText(get_description(self.FEC))

        self.cec_label = QLabel("CEC", self)
        self.cec_block = QTextEdit(self)
        self.cec_block.setPlainText(get_description(self.CEC))

        self.time_label = QLabel(str(self.current_time), self)
        self.button = QPushButton("Next", self)
        self.button.clicked.connect(self.button_clicked)

        self.timer = QTimer()
        self.timer.timeout.connect(self.button_clicked)

        self.check_run = QCheckBox("SpeedRun On/Off", self)
        self.check_run.stateChanged.connect(self.run_check_changed)

        layout = QHBoxLayout(self)

        layout1 = QVBoxLayout(self)
        layout2 = QVBoxLayout(self)

        layout1.addWidget(self.fec_label)
        layout1.addWidget(self.fec_text)
        layout2.addWidget(self.cec_label)
        layout2.addWidget(self.cec_block)
        layout1.addWidget(self.time_label)
        layout2.addWidget(self.info_label)
        layout1.addWidget(self.button)
        layout2.addWidget(self.check_run)

        layout.addLayout(layout1)
        layout.addLayout(layout2)

        self.setWindowTitle("Simulation")
        self.setGeometry(300, 300, 1200, 600)

        self.update_gui()
        self.show()

    def update_gui(self):
        self.info_label.setText(self.generate_stat())
        info_str = "id\ttime\tstatus\tdetails\n"
        self.fec_text.setPlainText(info_str+get_description(self.FEC))
        self.cec_block.setPlainText(info_str+get_description(self.CEC))
        s = "Текущее время: " + str(self.current_time)
        s += " Св. наладчики: " + str(self.free_workers)
        s +=  " Текущая фаза: "
        if self.timer_state != "FP":
            s += " Фаза просмотра"
        else:
            s += " Фаза коррекции таймера"
        self.time_label.setText(s)

    def generate_stat(self):
        s = f"Max idle = {self.max_idle}\nMax tuning = {self.max_tuning}\n"
        s += f"Max busy workers = {self.max_busy_workers}\n"
        s += f"Avr idle = {self.avr_idle}\n"
        s += f"Avr tuning = {self.avr_tuning}\n"
        s += f"Avr busy workers = {self.avr_busy_workers}\n"
        return str(s)

    def run_check_changed(self):
        self.speedrun = not self.speedrun
        if self.speedrun:
            self.timer.start(1)
        else:
            self.timer.stop()


    def button_clicked(self):
        # FP - FCT
        if self.timer_state == "FP":
            self.timer_state = "FCT"

            min_m = get_min_time_machine(self.FEC)

            self.prev_time = self.current_time
            self.current_time = min_m.time

            fec = self.FEC.copy()
            for m in fec:
                if m.time == self.current_time:
                    if m.details == 0 or m.details == 1:
                        m.log_text = f"working\t{m.details}->{m.details+1}"
                        m.details += 1
                        self.CEC.append(m)
                        self.FEC.remove(m)
                    elif m.state == "working" and not (((m.details+1) % self.max_detail) == 0):
                        m.log_text = f"working\t{m.details}->{m.details+1}"
                        m.details += 1
                        self.CEC.append(m)
                        self.FEC.remove(m)
                    elif m.state == "working" and (((m.details+1) % self.max_detail) == 0):
                        if self.free_workers > 0:
                            m.log_text = f"working->tuning\t{m.details}->{m.details+1}"
                            self.free_workers -= 1
                            m.state = "tuning"

                        else:
                            m.log_text = f"working->idle\t{m.details}->{m.details+1}"
                            m.state = "idle"
                        m.details += 1
                        self.CEC.append(m)
                        self.FEC.remove(m)
                    elif m.state == "tuning":
                        m.log_text = f"tuning->working\t{m.details}"
                        self.free_workers += 1
                        m.state = "working"
                        self.CEC.append(m)
                        self.FEC.remove(m)

        elif self.timer_state == "FCT":
            self.timer_state = "FP"

            cec = self.CEC.copy()
            for m in cec:
                if m.state == "working":
                    m.log_text = f"working\t{m.details}"
                    m.time += r_t(self.l_tc)
                    self.FEC.append(m)
                    self.CEC.remove(m)
                elif m.state == "tuning":
                    m.log_text = f"tuning\t{m.details}"
                    m.time += r_t(self.l_ts)
                    self.FEC.append(m)
                    self.CEC.remove(m)
                elif m.state == "idle":
                    if self.free_workers > 0:
                        m.log_text = f"tuning\t{m.details}"
                        m.state = "tuning"
                        self.free_workers -= 1
                        m.time = self.current_time + r_t(self.l_ts)
                        self.FEC.append(m)
                        self.CEC.remove(m)
                    else:
                        m.log_text = f"idle\t{m.details}"
                        m.time = self.current_time

        else:
            assert(0)

        # STATISTIC
        if self.timer_state == "FCT":
            idle_count = 0
            tuning_count = 0

            self.all_dt.append(self.current_time-self.prev_time)

            for m in self.CEC:
                if m.state == "idle":
                    idle_count += 1
            self.idle_counts.append(idle_count)

            if self.max_idle < idle_count:
                        self.max_idle = idle_count

            for m in self.FEC:
                if m.state == "tuning":
                    tuning_count += 1
            self.tuning_counts.append(tuning_count)

            if self.max_tuning < tuning_count:
                        self.max_tuning = tuning_count

            busy_workers = self.Z - self.free_workers
            if busy_workers > self.max_busy_workers:
                self.max_busy_workers = busy_workers
            self.busy_workers_counts.append(busy_workers)

            if self.current_time != 0:
                self.avr_idle = np.round(sum([idle*dt/self.current_time for dt,idle in zip(self.all_dt, self.idle_counts)]), 2)
                self.avr_tuning = np.round(sum([tune*dt/self.current_time for dt,tune in zip(self.all_dt, self.tuning_counts)]), 2)
                self.avr_busy_workers = np.round(sum([busy*dt/self.current_time for dt,busy in zip(self.all_dt, self.busy_workers_counts)]), 2)

        self.update_gui()

def get_min_time_machine(m_list):
    min_m = Machine(0, 999999)
    for m in m_list:
        if m.time < min_m.time:
            min_m = m
    return min_m

def get_description(m_list):
    s = ""
    for m in m_list:
        s += str(m) + "\n"
    return s

class Machine:
    def __init__(self, id, time, state="working"):
        self.id = id
        self.time = time
        self.state = state
        self.details = 0

        self.log_text = "working\t0"

    def __str__(self):
        # return "{}\t{}\t{}\t{}".format(self.id, self.time, self.state, self.details)
        return "{}\t{}\t{}".format(self.id, self.time, self.log_text)

def r_t(l):
    return int(-1/l*np.log(random.random()))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    sys.exit(app.exec_())