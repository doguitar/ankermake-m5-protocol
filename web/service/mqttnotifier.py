import time
import logging as log

from datetime import datetime

from ..lib.service import Service
from .. import rpcutil, app

from libflagship.mqtt import MqttMsgType


def mqtt_to_jsonrpc_req(data):
    update = {
        "eventtime": datetime.now().timestamp(),
    }

    cmd = data.get("commandType", 0)
    if cmd == MqttMsgType.ZZ_MQTT_CMD_HOTBED_TEMP:
        app.hotbed_target_temp = float(data["targetTemp"]) / 100
        update["heater_bed"] = {
            "temperature": float(data["currentTemp"]) / 100,
            "target": app.hotbed_target_temp,
            "power": None,
        }
    elif cmd == MqttMsgType.ZZ_MQTT_CMD_NOZZLE_TEMP:
        app.heater_target_temp = float(data["targetTemp"]) / 100
        update["extruder"] = {
            "temperature": float(data["currentTemp"]) / 100,
            "target": app.heater_target_temp,
            "power": 0,
            "can_extrude": True,
            "pressure_advance": None,
            "smooth_time": None,
            "motion_queue": None,
        }
    elif cmd == MqttMsgType.ZZ_MQTT_CMD_GCODE_COMMAND:
        return rpcutil.make_jsonrpc_req("notify_gcode_response", data["resData"])
    else:
        return None

    return rpcutil.make_jsonrpc_req("notify_status_update", update)


class MqttNotifierService(Service):

    def _handler(self, data):
        upd = mqtt_to_jsonrpc_req(data)
        if not upd:
            return

        for ws in app.websockets:
            ws.send(upd)

    def worker_start(self):
        self.mqtt = app.svc.get("mqttqueue")

        self.mqtt.handlers.append(self._handler)

    def worker_run(self, timeout):
        self.idle(timeout=timeout)

    def worker_stop(self):
        self.mqtt.handlers.remove(self._handler)

        app.svc.put("mqttqueue")
