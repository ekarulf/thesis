#!/usr/bin/env python
import re
import sys
import time
import calendar
import gdata.spreadsheet.service
import os

# Counters
FPS_TIME  = 0.0
TPS_TIME  = 0.0
RTS_TIME  = 0.0

class Robot(object):
    IDLE, MOVING, DIRECT = range(3)
    
    def __init__(self, epoch):
        self.state = None
        self.state_begin = None
        self.state_times = {}
        for state in (Robot.IDLE, Robot.MOVING, Robot.DIRECT):
            self.state_times[state] = 0.0
        
        self.neglect_begin = None
        self.neglect_time = 0.0

        self.selected = False
        
        self.set_state(Robot.IDLE, epoch)
        self.set_selected(False, epoch)
    
    def set_state(self, state, timestamp):
        if not self.state == state:
            if self.state in self.state_times:
                self.state_times[self.state] += timestamp - self.state_begin
            self.state = state
            self.state_begin = timestamp
        self.update_neglected(timestamp)
    
    def set_selected(self, selected, timestamp):
        if not self.selected == selected:
            self.selected = selected
        if self.state == Robot.DIRECT and not selected:
            self.set_state(Robot.IDLE, timestamp)
        self.update_neglected(timestamp)
    
    def update_neglected(self, timestamp, terminating=False):
        neglected = self.is_neglected()
        if neglected and self.neglect_begin is None:
            self.neglect_begin = timestamp
        elif not neglected and not self.neglect_begin is None or terminating:
            self.neglect_time += timestamp - self.neglect_begin
            self.neglect_begin = None
        
    def is_neglected(self):
        return self.state not in (Robot.MOVING, Robot.DIRECT) and not self.selected
            

class UI(object):
    RTS, TPS, FPS = range(3)
    
    def __init__(self, epoch):
        self.state = None
        self.state_times = {}
        for state in (UI.RTS, UI.TPS, UI.FPS):
            self.state_times[state] = 0.0
        self.begin = None
        self.switches = 0
        self.set_state(UI.RTS, epoch)

    def set_state(self, state, timestamp):
        if not self.state == state:
            if self.state in self.state_times:
                self.state_times[self.state] += timestamp - self.begin
            self.state = state
            self.begin = timestamp
            self.switches += 1

def main(filename):
    m = re.match("./(\d{2}\-\d{2})/(\w+)/[^\[]+\[(\d+)\]", filename)
    if m:
        user_id, experiment, run_id = m.group(1, 2, 3)
    else:
        user_id = filename
        run_id = experiment = None
    
    robots = {}
    initialized = False
    selected = []
    epoch = None
    with open(filename, 'r') as f:
        for lineno, line in enumerate(f.readlines()):
            fields = line.strip().split('\t')
            try:
                timestamp = calendar.timegm(time.strptime(fields[0], "%H:%M:%S"))
                msg_type  = fields[1]
                extra     = fields[2] if len(fields) >= 2 else ""
            except IndexError:
                print "Skipping line %d" % lineno
                continue
            # Initialize!
            if not initialized:
                for name in ["Blood", "Sweat"]:
                    robots[name] = Robot(timestamp)
                ui = UI(timestamp)
                epoch = timestamp
                initialized = True
            # Switch based on message type
            #
            # General Messages
            #
            if msg_type == 'mode switched to':
                if extra == 'TPD':
                    ui.set_state(UI.TPS, timestamp)
                elif extra == 'FPD':
                    ui.set_state(UI.FPS, timestamp)
                elif extra == 'Supervisor':
                    ui.set_state(UI.RTS, timestamp)
                else:
                    print "BAD HOODOO! (invalid mode on line %d)" % lineno
                    sys.exit(1)
            elif msg_type == 'selection changed to':
                old_selected = selected
                selected = []
                for name in extra.split(', '):
                    try:
                        selected.append(robots[name])
                    except KeyError:
                        continue
                # Deselect old robots
                for robot in old_selected:
                    if robot not in selected:
                        robot.set_selected(False, timestamp)
                # Select new robots
                for robot in selected:
                    if robot not in old_selected:
                        robot.set_selected(True, timestamp)
            elif msg_type == 'notification event':
                match = re.match(r'^\[\w+\] (\w+): Movement', extra)
                if match:
                    try:
                        robot = robots[match.group(1)]
                    except KeyError:
                        continue
                    else:
                        robot.set_state(Robot.IDLE, timestamp)
            #
            # Supervisor Messages
            #
            elif msg_type == 'done issuing task' and extra == 'Move':
                for robot in selected:
                    robot.set_state(Robot.MOVING, timestamp)
            #
            # Third / First Person Messages
            #
            elif msg_type in ('third-person direct mode event',
                              'first-person direct mode event'):
                assert len(selected) == 1, "Should only be one robot selected"
                if re.match("^arrow_(\w+)$", extra):
                    for robot in selected:
                        robot.set_state(Robot.DIRECT, timestamp)
                elif re.match("^arrow_(\w+)_up$", extra):
                    for robot in selected:
                        robot.set_state(Robot.IDLE, timestamp)
            else:
                print "No handler for Line %d: %s" % (lineno, repr(fields))
    # Finished parsing file, close state
    # Relies on timestamp fallthrough from for loop... bad style
    ui.set_state(None, timestamp)
    for robot in robots.values():
        robot.set_selected(False, timestamp)
        robot.set_state(None, timestamp)
        robot.update_neglected(timestamp, True)
    # Print Interesting Stats Here!
    print
    print "Total Time: %d" % (timestamp - epoch)
    print \
"""UI Stats
--------
Supervisor Time: %d
3rd Direct Time: %d
1st Direct Time: %d
Mode Changes:    %d
""" % (ui.state_times[UI.RTS], ui.state_times[UI.TPS], ui.state_times[UI.FPS], ui.switches)

    for name, robot in robots.items():
        print \
"""%s
--------
Neglect Time: %d
Idle Time:    %d
Moving Time:  %d
Direct Time:  %d
""" % (name, robot.neglect_time, robot.state_times[Robot.IDLE], 
       robot.state_times[Robot.MOVING], robot.state_times[Robot.DIRECT])
    
    # INSERT INTO SPREADSHEET
    SpreadsheetInsert({
        'blooddirects': robots["Blood"].state_times[Robot.DIRECT],
        'bloodidles': robots["Blood"].state_times[Robot.IDLE],
        'bloodmovings': robots["Blood"].state_times[Robot.MOVING],
        'bloodneglects': robots["Blood"].neglect_time,
        'completion': timestamp - epoch,
        'experiment': experiment,
        'id': user_id,
        'modeswitches': ui.switches,
        'run': run_id,
        'sweatdirects': robots["Sweat"].state_times[Robot.DIRECT],
        'sweatidles': robots["Sweat"].state_times[Robot.IDLE],
        'sweatmovings': robots["Sweat"].state_times[Robot.MOVING],
        'sweatneglects': robots["Sweat"].neglect_time,
        'timein1sts': ui.state_times[UI.FPS],
        'timein3rds': ui.state_times[UI.TPS],
        'timeinsupervisors': ui.state_times[UI.RTS],
        'timetobox1': None,
        'timetobox2': None,
        'timetobox3': None,
        'totaldirecttimes': robots["Sweat"].state_times[Robot.DIRECT] + robots["Blood"].state_times[Robot.DIRECT],
        'totalidletimes': robots["Sweat"].state_times[Robot.IDLE] + robots["Blood"].state_times[Robot.IDLE],
        'totalmovingtimes': robots["Sweat"].state_times[Robot.MOVING] + robots["Blood"].state_times[Robot.MOVING],
        'totalneglecttimes': robots["Sweat"].neglect_time + robots["Blood"].neglect_time,
        'typeierrors': None,
        'typeiierrors': None,
    })

def SpreadsheetInsert(data):
    gd_client = gdata.spreadsheet.service.SpreadsheetsService()
    gd_client.email = 'ekarulf@gmail.com'
    gd_client.password = os.getenv("GMAIL_PASSWORD")
    gd_client.source = "FooBar"
    gd_client.ProgrammaticLogin()
    
    SPREADSHEET_ID = '0AuFk0R2ReTQHdE9JZHFBc0M4NmpndlQ4U2RNcmh3ZVE'
    WORKSHEET_ID = 'oda'
    for key, value in data.items():
        if value is not None and not type(value) == str:
            data[key] = str(value)
    gd_client.InsertRow(data, SPREADSHEET_ID, WORKSHEET_ID)
    

if __name__ == '__main__':
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        main(filename)
    else:
        print "usage: %s filename" % sys.argv[0]
