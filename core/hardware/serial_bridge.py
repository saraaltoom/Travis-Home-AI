import serial
import time
import os
try:
    from serial.tools import list_ports
except Exception:
    list_ports = None


class SerialBridge:
    def __init__(self, port="COM4", baudrate=9600, timeout=1):
        self.port = port or "COM4"
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self._connect()

    def _connect(self):

        env_port = os.environ.get("TRAVIS_SERIAL_PORT")
        if env_port:
            self.port = env_port

        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout, write_timeout=1)
        except Exception as e:
            print(f"[Serial] Failed to connect on {self.port}: {e}")
            self.ser = None

            if list_ports is not None:
                try:
                    candidates = list(list_ports.comports())

                    preferred = [p.device for p in candidates if any(k in (p.description or '').lower() for k in ["arduino", "usb serial", "ch340", "cp210", "silabs"]) ]
                    search = preferred or [p.device for p in candidates]
                    for dev in search:
                        try:
                            self.ser = serial.Serial(dev, self.baudrate, timeout=self.timeout, write_timeout=1)
                            self.port = dev
                            break
                        except Exception:
                            self.ser = None
                except Exception:
                    pass
        if self.ser:

            time.sleep(2)
            try:
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
            except Exception:
                pass
            print(f"[Hardware] Connected to Arduino on {self.port} @ {self.baudrate}.")

    def is_connected(self):
        return bool(self.ser and self.ser.is_open)

    def send(self, message: str):
        if not isinstance(message, str):
            message = str(message)
        if not self.is_connected():
            print("[SerialBridge] Not connected. Attempting reconnect...")
            self._connect()
        if self.is_connected():
            try:
                payload = (message.strip() + "\n").encode("utf-8")
                self.ser.write(payload)
                self.ser.flush()
                print(f"[SerialBridge] Sent: {message}")
            except Exception as e:
                print(f"[SerialBridge] Error sending: {e}")
        else:
            print("[SerialBridge] Not connected.")

    def readline(self, timeout_s: float = 1.0) -> str:
        if not self.is_connected():
            return ""
        end = time.time() + max(0.05, timeout_s)
        line = b""
        while time.time() < end:
            try:
                if self.ser.in_waiting:
                    b = self.ser.read_until(b"\n")
                    try:
                        return b.decode("utf-8", errors="ignore").strip()
                    except Exception:
                        return ""
                time.sleep(0.01)
            except Exception:
                break
        return ""

    def read_available(self, max_lines: int = 10, timeout_s: float = 1.0):
        lines = []
        for _ in range(max(1, max_lines)):
            s = self.readline(timeout_s=timeout_s)
            if not s:
                break
            lines.append(s)
        return lines

    def close(self):
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
                print("[SerialBridge] Connection closed.")
        except Exception:
            pass
