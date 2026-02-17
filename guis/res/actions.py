
import os
import subprocess

from PyQt5.QtWidgets import QLabel
import time


SSID = 'marco\'s iPhone'
PASSWORD = 'Manodicea7'


class Actions:

    @staticmethod
    def carplay_action():
        os.system("/home/braga/Desktop/Carplay")

    @staticmethod
    def youtube_action():
        os.system("freetube")

    @staticmethod
    def primevideo_action():
        print("primevideo")

    @staticmethod
    def hotspot_action(label: QLabel):
        prec = label.text()
        label.setText("Attempting hotspot connection ...")
        if Actions.is_connected():
            label.setText("Hotspot connection already active.")
            time.sleep(2)
            label.setText(prec)
        else:
            try:
                Actions.reconnect()
                label.setText("Hotspot connection active.")
            except subprocess.CalledProcessError:
                label.setText("Failed to connect to hotspot.")
            finally:
                time.sleep(2)
                label.setText(prec)

    @staticmethod
    def is_connected():
        """Check if Pi is connected to the given SSID."""
        try:
            output = subprocess.check_output(
                ["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"],
                text=True
            )
            for line in output.strip().split("\n"):
                active, ssid = line.split(":")
                if active == "yes" and ssid == SSID:
                    return True
        except subprocess.CalledProcessError:
            pass
        return False

    @staticmethod
    def reconnect():
        """Try to connect to the WiFi network."""
        try:
            print(f"Attempting to connect to {SSID}...")
            subprocess.check_call(
                ["nmcli", "dev", "wifi", "connect", SSID, "password", PASSWORD]
            )
            print("Connected successfully!")
        except subprocess.CalledProcessError as e:
            print("Failed to connect:", e)
            raise subprocess.CalledProcessError
