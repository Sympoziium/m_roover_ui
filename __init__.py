"""UI Flask de Roover Mk1, preparée pour devenir un sous-module git.

Le code de ce paquet est volontairement autonome pour pouvoir etre extrait en
`m_roover_ui` sans embarquer le bootstrap materiel du robot.
"""

from .flask_router import register_routes
from .server_controller import ServerController
