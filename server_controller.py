#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Controleur Flask minimaliste pour Roover Mk1 (UI + mode test)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import cv2
from flask import Flask, Response, jsonify, render_template_string, request

if TYPE_CHECKING:
    from core.control.control_manager import ControlManager
    from roover.core.vision.vision_pipeline import VisionPipeline

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
##################################################################
#   Constantes
##################################################################

    _MANUAL_DRIVE_SPEED = 60
    _MANUAL_TURN_SPEED = 45

    def __init__(self, robot, debug=False):
        """Instance du serveur Flask pour l'interface web de Roover Mk1.
        
        Args:
            robot: Instance de la classe Robot.
            debug: Si True, active le mode debug Flask (rechargement auto).
        """
        self.robot = robot
        self.control_manager: ControlManager | None = None
        self.vision_pipeline: VisionPipeline | None = None
        self.debug = debug

        self.app = Flask(__name__)
        self.app.config['TEMPLATES_AUTO_RELOAD'] = True

##########################################################
#  Fonctions protégées
##########################################################

    @property
    def _get_control_manager(self):
        """Getter pour le ControlManager attaché au ServerController."""
        return self.control_manager

    @property
    def _get_manual_controller(self):
        """Getter pour le ManualController attaché au ControlManager."""
        if self.control_manager is None:
            return None
        return self.control_manager.get_controller('manual_controller')
    
    @property
    def _get_vision_pipeline(self):
        """Getter pour le VisionPipeline attaché au ServerController."""
        return self.vision_pipeline

##########################################################
#  Setters
##########################################################

    def SC_Set_Control_Manager(self, control_manager:ControlManager):
        """
        Setter pour attacher le ControlManager au ServerController.
        Args:
            control_manager: Instance de ControlManager.
        """
        self.control_manager = control_manager

    def SC_Set_Vision_Pipeline(self, vision_pipeline:VisionPipeline):
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
        if self.control_manager is None:
            return jsonify({'error': 'ControlManager non attache'}), 500

        ctrl_mgr = self.control_manager
        ctrl = ctrl_mgr.get_active_controller()
        if ctrl is None or ctrl.name != 'manual_controller':
            ctrl_mgr.activate_controller('manual_controller')

        data = request.get_json(silent=True) or {}
        keys = set(k.lower() for k in data.get('keys', []))
        command = ''.join(key for key in 'wasd' if key in keys)

        # Dispatch des commandes manuelles vers le ControlManager
        ctrl_mgr.update_command(command)

        return ('', 204)

    def control_stop(self):
        """
        Description:
            Endpoint pour envoyer automatiquement un stop 
            au robot lorsque l'utilisateur relâche toutes les touches de contrôle.
        Returns:
            Response: Objet Flask Response indiquant le succès ou l'échec de l'arrêt du contrôle.
        """
        if self.control_manager is None:
            return jsonify({'error': 'ControlManager non attache'}), 500
        
        ctrl_mgr = self.control_manager

        ctrl_mgr.update_command('STOP')

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
