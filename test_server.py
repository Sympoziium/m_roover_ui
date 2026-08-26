"""
test_server.py

Description:
    Serveur de test pour le module m_roover_ui. Il permet de simuler un robot et un ControlManager
    afin de tester l'interface web sans avoir besoin du robot physique.

Usage:
    dans un terminal, naviguer vers le dossier RoverMk1/ puis lancer:
        python -m roover.m_roover_ui.test_server

"""

from __future__ import annotations

import argparse

import cv2
import numpy as np

try:
    from .flask_router import register_routes
    from .server_controller import ServerController
except ImportError:
    from roover.m_roover_ui.flask_router import register_routes
    from roover.m_roover_ui.server_controller import ServerController


class MockManualController:
    name = 'manual_controller'

    def __init__(self):
        self._throttle = 0
        self._steering = 0
        self._drive_speed = 60
        self._turn_speed = 45

    @staticmethod
    def compute_speeds(throttle, steering, drive_speed, turn_speed, steering_ratio=0.5):
        if throttle == 0 and steering == 0:
            return (0, 0)
        if throttle == 0:
            return (steering * turn_speed, -steering * turn_speed)

        base = throttle * drive_speed
        if steering == 0:
            return (base, base)

        half_diff = base * steering_ratio
        inner = base - half_diff
        outer = base + half_diff
        if steering < 0:
            return (inner, outer)
        return (outer, inner)

    def start(self):
        self._throttle = 0
        self._steering = 0

    def stop(self):
        self._throttle = 0
        self._steering = 0

    def set_compound_action(self, throttle, steering, drive_speed=None, turn_speed=None):
        self._throttle = throttle
        self._steering = steering
        if drive_speed is not None:
            self._drive_speed = drive_speed
        if turn_speed is not None:
            self._turn_speed = turn_speed


class MockControlManager:
    def __init__(self, robot):
        self.robot = robot
        self._controllers = {'manual_controller': MockManualController()}
        self._active_controller = None
        self.last_left_speed = 0
        self.last_right_speed = 0
        self.manual_override_active = False

    def get_controller(self, name):
        return self._controllers.get(name)

    def activate_controller(self, name):
        controller = self.get_controller(name)
        if controller is None:
            raise ValueError(f"Contrôleur '{name}' non trouvé.")
        if self._active_controller is not None:
            self._active_controller.stop()
        self._active_controller = controller
        controller.start()

    def deactivate_controller(self):
        if self._active_controller is not None:
            self._active_controller.stop()
        self._active_controller = None
        self.last_left_speed = 0
        self.last_right_speed = 0
        self.robot.stop()

    def clear_manual_override(self):
        self.manual_override_active = False

    def update_last_command_from_controller(self, controller):
        left, right = controller.compute_speeds(
            controller._throttle,
            controller._steering,
            controller._drive_speed,
            controller._turn_speed,
        )
        self.last_left_speed = left
        self.last_right_speed = right
        self.robot.set_wheel_speeds(left, right)


class MockRobot:
    def __init__(self):
        self.last_left = 0
        self.last_right = 0

    def set_wheel_speeds(self, left, right):
        self.last_left = left
        self.last_right = right
        print(f"[MOCK ROBOT] wheels left={left} right={right}")

    def stop(self):
        self.set_wheel_speeds(0, 0)


class MockCamera:
    def __init__(self):
        self._counter = 0

    def capture(self):
        self._counter += 1
        frame = np.zeros((360, 640, 3), dtype=np.uint8)
        frame[:, :] = (20, 40, 70)
        cv2.putText(frame, 'm_roover_ui test', (20, 60), cv2.FONT_HERSHEY_SIMPLEX,
                    1.1, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, f'frame #{self._counter}', (20, 110), cv2.FONT_HERSHEY_SIMPLEX,
                    0.9, (255, 220, 120), 2, cv2.LINE_AA)
        cv2.circle(frame, (320, 220), 65, (40, 180, 240), 4)
        return frame


class MockVisionPipeline:
    def __init__(self):
        self.camera = MockCamera()
        self._running = True
        self.last_frame = None

    def is_running(self):
        return self._running

    def update_last_frame(self, frame):
        self.last_frame = frame

    def start_passive_detection(self):
        return None

    def stop_passive_detection(self):
        return None


def create_app():
    robot = MockRobot()
    controller = ServerController(robot, debug=True)
    controller.SC_Set_Control_Manager(MockControlManager(robot))
    controller.SC_Set_Vision_Pipeline(MockVisionPipeline())
    return register_routes(controller)


def main():
    parser = argparse.ArgumentParser(description='Lance le serveur de test m_roover_ui.')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=5001)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()

    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)


if __name__ == '__main__':
    main()
