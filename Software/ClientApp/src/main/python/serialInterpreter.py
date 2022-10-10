import glob
import sys
import json

from serial import Serial
from serial.tools import list_ports
from time import sleep
from gui_elements.protocol.PoTConstants import *
from PyQt5 import QtCore, QtWidgets, Qt


class SerialInterpreter:

    def __init__(self, parent=None):
        """Initialize class vars and find Serial connection if possible"""
        self.serialPrompt = b"Paddle>"
        self.testMessage = b"paddlePing\r"
        self.testResponse = b"paddlePong\r\n"

        self.serial = Serial(baudrate=9600, timeout=0.05)
        self.parent = parent
        self.serialConn = None

        while self.serialConn is None:
            self.serialConn = self.find_serial_connection()
            sleep(1)

        self.parent.splash.showMessage(f"Connecting to {self.serialConn}", QtCore.Qt.AlignCenter | QtCore.Qt.AlignBottom,  color=QtCore.Qt.white)
        print("Found serial connection at {0}".format(self.serialConn))
        self.serial.open()

    def test_serial_connection(self, inPort):
        """Test an individual serial connection to see whether it returns the POT handshake

        :param inPort: String name for the port
        :return: True == This serial port connects to the Paddle
        """
        self.serial.port = inPort

        try:
            self.serial.open()
        except Exception:
            return False

        # if you're getting the serial for the first time, read through the fixed prompt
        string = ""
        if self.serial.read_until():
            while string != self.serialPrompt:
                string = self.serial.read_until()

        # Attempt the handshake
        self.serial.write(self.testMessage)
        self.serial.read_until()  # throw away first newline
        response = self.serial.read_until()
        if response == self.testResponse:
            self.serial.close()
            return True

        self.serial.close()
        return False

    def send_serial_command(self, cmd, argument=None):
        """ Send command `cmd` optionally with arg `argument` to the paddle, return multi-line string response

        :param cmd: The command to send
        :param argument: OPTIONAL value to set for the command
        :return: string response, else None
        """
        if argument is not None:
            cmd_str = "{0}={1}\r".format(cmd, str(argument).upper()).encode(encoding="UTF-8")
        else:
            cmd_str = cmd

        print(f"About to send {cmd_str}")
        self.serial.write(cmd_str)

        message = ""
        latest = b""
        # return message one line at a time until we get the prompt
        if cmd is not CMD_EXIT:
            while latest != self.serialPrompt:
                message += latest.decode(encoding="UTF-8")
                latest = self.serial.read_until()

        if message == "":
            message = None
        return message

    def find_serial_connection(self):
        """return name of serial connection if possible, else None"""
        if sys.platform.startswith('win'):
            for comport_struct in list_ports.comports():
                if self.test_serial_connection(comport_struct.name):
                    return comport_struct.name

        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            for port_str in glob.glob('/dev/tty?*'):  # trick to find all TTYs except `/dev/tty`
                if self.test_serial_connection(port_str):
                    return port_str
        else:
            raise RuntimeError('Only Windows, Linux, and Cygwin are supported!')
        return None

    def set_gui_config_from_serial(self, config_dict):
        """ send command to get all config, update config from response """
        response_str = self.send_serial_command(CMD_ALL_CONFIG)
        if not response_str:
            raise RuntimeError('Got no response from paddle')

        result_obj = json.loads(response_str)
        for key in result_obj[STR_ALL_CONFIGS].keys():
            this_config = result_obj[STR_ALL_CONFIGS][key]
            config_dict[key]["control"] = this_config["control"],
            config_dict[key]["pitchbend"] = this_config["pitchbend"],
            config_dict[key]["offset1"] = this_config["offset1"],
            config_dict[key]["offset2"] = this_config["offset2"],
            config_dict[key]["offset3"] = this_config["offset3"],
            config_dict[key]["octave"] = this_config["octave"],
            config_dict[key]["root_note"] = this_config["root_note"],
            config_dict[key]["mode"] = this_config["mode"],
            config_dict[key]["enable"] = this_config["enable"]

            # TODO figure out if these are needed at all
            # pb_is_cc = (int(this_config["pitchbend"]) != MIDI_CC_P_BEND),
            # pb_enable = ("TRUE" if (this_config["pitchbend"]) < 128 or int(this_config["pitchbend"] == MIDI_CC_P_BEND)
            #              else "FALSE"),
            # pb_value = this_config["pitchbend"],
