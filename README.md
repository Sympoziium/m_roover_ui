# m_roover_ui
UI repository for rover project.

## Index
- [Index](#index)
- [Description générale](#description-générale)
- [Utilisation](#utilisation)
- [Description des composants](#description-des-composants)

---
## Description générale

---
## Utilisation

---
## Description des composants
### cnn_utils.py
#### Description
Ce module contient des fonctions utilitaires pour le traitement d'images et la manipulation de modèles CNN.

#### Utilisation
Pour utiliser les fonctions de ce module, vous devez importer le fichier `cnn_utils.py` dans votre script Python. Vous pouvez ensuite appeler les fonctions disponibles pour effectuer des opérations sur les images et les modèles CNN.

#### Dépendances
- numpy
- cv2

#### Liste des fonctions
- `extract_frame_from_state(state)`: Extrait une image à partir d'un état donné. (À compléter, il faut attribuer un etat)
- `preprocess_frame(frame, input_shape)`: Prétraite une image pour convertir du format OpenCV à TFLite pour l'entrée dans un modèle CNN.

### flask_router.py
#### Description
Ce module contient des fonctions pour gérer les routes et les requêtes HTTP dans une application Flask.

#### Utilisation
Pour utiliser les fonctions de ce module, vous devez importer le fichier `flask_router.py` dans votre script Python. Vous pouvez ensuite définir des routes et gérer les requêtes HTTP dans votre application Flask.

#### Dépendances
-
### onglet_control.py

### server_controller.py

### test_server.py


### Architecture du projet

**Décision de concept initial**
pour commencer je veux simplement pouvoir contrôler le robot manuellement avec WASD. on va donc hardcoder les touches et les actions associées pour avoir un premier prototype fonctionnel.




---