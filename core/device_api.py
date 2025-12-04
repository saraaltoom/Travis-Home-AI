

"""
Unified device API helpers that send clear text commands to Arduino
via the shared SerialBridge, avoiding multiple processes opening COM4.

Expected Arduino commands (newline-terminated):
 - "open door"
 - "close door"
 - "light off" | "light low" | "light medium" | "light high"
"""

from typing import Dict


def execute_device_action(data: Dict, serial_bridge):
    """
    Send a device action in text form over the provided serial bridge.

    data example: {"action": "turn_on", "device": "light", "level": "high"}
    """
    if not serial_bridge or not serial_bridge.is_connected():
        print("[Hardware] No Arduino connection.")
        return

    action = (data or {}).get("action")
    device = (data or {}).get("device")
    level = (data or {}).get("level")

    if not action or not device:
        print("[Hardware] Missing info in command.")
        return

    if device == "door":
        if action in ("open", "unlock"):
            serial_bridge.send("open door")
        elif action in ("close", "lock"):
            serial_bridge.send("close door")
        else:
            print(f"[Hardware] Unknown door action: {action}")
    elif device == "light":

        if action in ("turn_on", "on") and not level:
            level = "high"
        if action in ("turn_off", "off"):

            serial_bridge.send("light off top")
            serial_bridge.send("light off bottom")
            return


        if level in ("low",):
            serial_bridge.send("light off top")
            serial_bridge.send("light off bottom")
        else:

            serial_bridge.send("light on top")
            serial_bridge.send("light on bottom")
    elif device in ("light_top", "light_bottom"):

        zone = "top" if device == "light_top" else "bottom"
        if action in ("turn_off", "off"):
            serial_bridge.send(f"light off {zone}")
        elif action in ("turn_on", "on"):

            serial_bridge.send(f"light on {zone}")
        else:
            print(f"[Hardware] Unknown action for {device}: {action}")
    else:
        print(f"[Hardware] Unknown device: {device}")
