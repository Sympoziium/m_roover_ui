#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Controleur Flask minimaliste pour Roover Mk1 (UI + mode test)."""

import time

import cv2
from flask import Flask, Response, jsonify, render_template_string, request

try:
    from .onglet_control import render_control_tab
except ImportError:
    from roover.m_roover_ui.onglet_control import render_control_tab


class ServerController:
    """Etat partage entre les routes Flask et le backend injection."""

    def __init__(self, robot, debug=False):
        self.robot = robot
        self.control_manager = None
        self.vision_pipeline = None
        self.debug = debug

        self.manual_drive_speed = 60
        self.manual_turn_speed = 45

        self.app = Flask(__name__)
        self.app.config['TEMPLATES_AUTO_RELOAD'] = True

    def attach_control_manager(self, control_manager):
        self.control_manager = control_manager

    def attach_pipeline_vision(self, vision_pipeline):
        self.vision_pipeline = vision_pipeline

    def home(self):
        return render_template_string(_HOME_HTML)

    def onglet_control(self):
        return render_control_tab()

    def video_feed(self):
        vp = self.vision_pipeline
        if vp is None or not vp.is_running():
            return ("Camera OFF", 503)

        def generate():
            while vp.is_running():
                try:
                    frame = vp.camera.capture()
                except Exception as exc:
                    print("[video_feed] erreur capture:", exc)
                    time.sleep(0.1)
                    continue

                if frame is None:
                    time.sleep(0.05)
                    continue

                vp.update_last_frame(frame)
                ok, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ok:
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                           + jpeg.tobytes() + b'\r\n')

        return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

    def controller_start_manual(self):
        if self.control_manager is None:
            return jsonify({'error': 'ControlManager non attache'}), 500
        if self.control_manager.get_controller('manual_controller') is None:
            return jsonify({'error': 'ManualController non enregistre'}), 500
        try:
            self.control_manager.activate_controller('manual_controller')
            return jsonify({'status': 'manual_controller activated'})
        except Exception as exc:
            return jsonify({'error': str(exc)}), 500

    def controller_stop(self):
        if self.control_manager is None:
            return jsonify({'error': 'ControlManager non attache'}), 500
        try:
            self.control_manager.deactivate_controller()
            return jsonify({'status': 'controller stopped'})
        except Exception as exc:
            return jsonify({'error': str(exc)}), 500

    def controller_status(self):
        if self.control_manager is None:
            return jsonify({'active': False, 'reason': 'ControlManager non attache'})
        active = self.control_manager._active_controller
        return jsonify({
            'active': active is not None,
            'name': active.name if active is not None else None,
            'left_speed': self.control_manager.last_left_speed,
            'right_speed': self.control_manager.last_right_speed,
        })

    def control_keys(self):
        if self.control_manager is None:
            return jsonify({'error': 'ControlManager non attache'}), 500

        ctrl = self.control_manager.get_controller('manual_controller')
        if ctrl is None:
            return jsonify({'error': 'ManualController non enregistre'}), 500

        data = request.get_json(silent=True) or {}
        keys = set(k.lower() for k in data.get('keys', []))
        throttle = (1 if 'w' in keys else 0) + (-1 if 's' in keys else 0)
        steering = (-1 if 'a' in keys else 0) + (1 if 'd' in keys else 0)

        ctrl.set_compound_action(
            throttle, steering,
            drive_speed=self.manual_drive_speed,
            turn_speed=self.manual_turn_speed,
        )
        self.control_manager.update_last_command_from_controller(ctrl)
        return ('', 204)

    def control_stop(self):
        if self.control_manager is None:
            return jsonify({'error': 'ControlManager non attache'}), 500
        ctrl = self.control_manager.get_controller('manual_controller')
        if ctrl is not None:
            ctrl.set_compound_action(0, 0)
            self.control_manager.update_last_command_from_controller(ctrl)
        if self.control_manager.manual_override_active:
            self.control_manager.clear_manual_override()
        return ('', 204)


controller = ServerController


_HOME_HTML = """<!doctype html>
<html lang='fr'><head>
<meta charset='utf-8'>
<title>Roover Mk1</title>
<style>
body { font-family: Segoe UI, Arial, sans-serif; background:#eef6fb; color:#234;
       margin:0; padding:2rem; }
h1 { color:#3a6ea5; }
a { color:#3a6ea5; font-size:1.1rem; }
</style>
</head><body>
<h1>Roover Mk1</h1>
<p>Suite post-PFE H2026 portee sur Freenove 4WD + Pi 4B.</p>
<ul>
  <li><a href='/onglet_control'>Controle manuel (WASD + live feed)</a></li>
</ul>
</body></html>
"""
