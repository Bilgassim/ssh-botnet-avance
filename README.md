# SSH Botnet Advanced (Python 3)

Une version avancée et optimisée du SSH Botnet, portée sous Python 3 avec un support multithread pour les scans de masse.

## Caractéristiques
- **Portage Python 3** : Entièrement compatible avec les environnements modernes.
- **Multithreading** : Utilise `ThreadPoolExecutor` pour scanner et exécuter des commandes sur des milliers d'hôtes en parallèle (50 workers par défaut).
- **Scan de masse** : Optimisé pour gérer des listes de plus de 150 000 hôtes.
- **Silence des logs** : Les erreurs de protocole SSH (bannières, timeouts) sont capturées silencieusement pour un affichage propre.
- **Indicateur de progression** : Suivi dynamique en temps réel lors de la vérification des hôtes.
- **Format flexible** : Supporte les fichiers d'identifiants au format CSV (`IP,user,password`) ou avec espaces.
- **Menu interactif** : Gestion complète des hôtes (listage, exécution de commandes, upload/download de fichiers, exécution de scripts).

## Installation

### Dépendances système
L'outil utilise `Fabric` et `Termcolor`. Sur Kali Linux :

```bash
sudo apt update
sudo apt install -y python3-fabric python3-termcolor
```

### Installation manuelle via pip
```bash
pip install fabric termcolor
```

## Utilisation

1. Lancez le script :
   ```bash
   python3 script.py
   ```

2. Entrez le chemin vers votre fichier de cibles lorsqu'il est demandé.
   *Exemple : `/home/kali/Desktop/ssh-bot/ssh_formatted.txt`*

3. Attendez la fin de la vérification des hôtes (suivez la barre de progression).

4. Utilisez le menu interactif :
   - `[0] List Hosts` : Affiche tous les hôtes et leur système.
   - `[1] Active Hosts` : Liste uniquement les hôtes qui ont répondu positivement.
   - `[3] Run Command` : Exécute une commande shell sur un ou plusieurs hôtes.
   - `[5] File Upload` : Envoie un fichier local vers les hôtes sélectionnés.
   - `[7] Script Exec` : Télécharge et exécute un script en arrière-plan sur les hôtes.

## Format du fichier d'hôtes
Le fichier doit contenir un hôte par ligne sous l'une des formes suivantes :
- `IP,utilisateur,mot_de_passe`
- `IP utilisateur mot_de_passe`

*Exemple :*
```text
192.168.1.10,root,toor
10.0.0.5 admin password123
```

## Sécurité et Performance
- Le script utilise un timeout de 2 secondes par hôte pour garantir une vitesse de scan maximale.
- Le nombre de threads (workers) peut être ajusté dans le fichier `script.py` (classe `SSHBotnet`, méthode `check_hosts`).

## Auteur
Bilgassim
