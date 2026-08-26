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
    """ServerController
    Classe de gestion du serveur Flask servant d'interface de contrôle pour le robot Roover Mk1.
    
    Description:
        Cette classe encapsule un serveur Flask servant à relier l'interface de contrôle web au robot.
        On y retrouve principalement les endpoints reliant les actions des boutons de l'interface aux
        méthodes fonctionnalités du robot.

    Attributes:
        robot: Instance de la classe Robot.
        control_manager: Instance de ControlManager.
        vision_pipeline: Instance de VisionPipeline.
        debug: Mode debug.

    Methods:
        SC_Set_Control_Manager(control_manager): Attache le ControlManager.
        SC_Set_Vision_Pipeline(vision_pipeline): Attache le VisionPipeline.
    """

    def __init__(self, robot, debug=False):
        """Instance du serveur Flask pour l'interface web de Roover Mk1.
        
        Args:
            robot: Instance de la classe Robot.
            debug: Si True, active le mode debug Flask (rechargement auto).
        """
        self.robot = robot
        self.control_manager = None
        self.vision_pipeline = None
        self.debug = debug

        self.manual_drive_speed = 60
        self.manual_turn_speed = 45

        self.app = Flask(__name__)
        self.app.config['TEMPLATES_AUTO_RELOAD'] = True

##########################################################
#  Setters
##########################################################

    def SC_Set_Control_Manager(self, control_manager):
        """
        Setter pour attacher le ControlManager au ServerController.
        Args:
            control_manager: Instance de ControlManager.
        """
        self.control_manager = control_manager

    def SC_Set_Vision_Pipeline(self, vision_pipeline):
        """
        Setter pour attacher le VisionPipeline au ServerController.
        Args:
            vision_pipeline: Instance de VisionPipeline.
        """
        self.vision_pipeline = vision_pipeline

##########################################################
#   Onglets
##########################################################

    def home(self):
        return render_template_string(_HOME_HTML)

    def onglet_control(self):
        return render_control_tab()

###########################################################
#   Endpoints
###########################################################

    def video_feed(self):
        """
        Endpoint pour le flux vidéo.
        
        Description:
            Cette méthode génère un flux vidéo en continu à partir de la caméra du robot.
            Elle encode chaque image en JPEG et les envoie au client via un flux multipart.

        Returns:
            Response: Objet Flask Response contenant le flux vidéo.
        """
        vp = self.vision_pipeline
        if vp is None or not vp.is_running():
            return ("Camera OFF", 503)

        def generate():
            while vp.is_running():
                try:
                    # capture de l'image depuis la caméra du robot
                    frame = vp.camera.capture()
                except Exception as exc:
                    print("[video_feed] erreur capture:", exc)
                    time.sleep(0.1)
                    continue

                if frame is None:
                    time.sleep(0.05)
                    continue
                # mise à jour de la dernière image dans le buffer du pipeline de vision
                vp.update_last_frame(frame)
                ok, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])

                if ok:
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                           + jpeg.tobytes() + b'\r\n')

        return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

    def controller_start_manual(self):
        """
        Description:
            Endpoint pour activer le contrôleur manuel.

        Returns:
            Response: Objet Flask Response indiquant le succès ou l'échec de l'activation.
        """
        # Vérification de l'attachement du ControlManager et du ManualController
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
        """
        Description:
            Endpoint pour arrêter le contrôleur.

        Returns:
            Response: Objet Flask Response indiquant le succès ou l'échec de l'arrêt.
        """
        if self.control_manager is None:
            return jsonify({'error': 'ControlManager non attache'}), 500
        try:
            self.control_manager.deactivate_controller()
            return jsonify({'status': 'controller stopped'})
        except Exception as exc:
            return jsonify({'error': str(exc)}), 500

    def controller_status(self):
        """
        Description:
            Endpoint pour obtenir le statut du contrôleur actif.
        Returns:
            Response: Objet Flask Response contenant le statut du contrôleur.
        """
        if self.control_manager is None:
            return jsonify({'active': False, 'reason': 'ControlManager non attache'})
        active_controller = self.control_manager._active_controller
        return jsonify({
            'active': active_controller is not None,
            'name': active_controller.name if active_controller is not None else None,
            'left_speed': self.control_manager.last_left_speed,
            'right_speed': self.control_manager.last_right_speed,
        })

    def control_keys(self):
        """
        Endpoint pour recevoir les commandes de contrôle manuel via les touches WASD.
        Description:
            Cette méthode reçoit les commandes de contrôle manuel envoyées par l'interface web.
            Elle interprète les touches WASD pour déterminer la vitesse de déplacement et de rotation du robot.
        Returns:
            Response: Objet Flask Response indiquant le succès ou l'échec du traitement des commandes.
        """
        Warning("This method hasent been integrated yet with the ControlManager. ")
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
        ### pas sur que ces sa la vraie fonction
        self.control_manager.update_last_command_from_controller(ctrl)
        return ('', 204)

    def control_stop(self):
        
        Warning("This method hasent been integrated yet with the ControlManager. ")
        """"""
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
