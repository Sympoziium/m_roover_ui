#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Enregistre les routes Flask de l'app Roover Mk1 minimale."""


def register_routes(ctrl):
    """Lie les URL aux methodes de `ServerController`."""
    app = ctrl.app

    app.add_url_rule('/', 'home', ctrl.home)
    app.add_url_rule('/onglet_control', 'onglet_control', ctrl.onglet_control)
    app.add_url_rule('/video', 'video_feed', ctrl.video_feed)
    app.add_url_rule('/controller/start_manual',
                     'controller_start_manual',
                     ctrl.controller_start_manual, methods=['POST'])
    app.add_url_rule('/controller/stop',
                     'controller_stop',
                     ctrl.controller_stop, methods=['POST'])
    app.add_url_rule('/controller/status',
                     'controller_status', ctrl.controller_status)
    app.add_url_rule('/control/keys', 'control_keys',
                     ctrl.control_keys, methods=['POST'])
    app.add_url_rule('/control/stop', 'control_stop',
                     ctrl.control_stop, methods=['POST'])

    return app
