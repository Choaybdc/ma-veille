# Mes rendez-vous — PWA Android

## Publication
Cette application est déposée dans le dossier `mes-rendez-vous/` du dépôt GitHub Pages `Choaybdc/ma-veille`. URL prévue : https://choaybdc.github.io/ma-veille/mes-rendez-vous/

## Configuration Google OAuth
1. Ouvrir Google Cloud Console : https://console.cloud.google.com/
2. Créer/sélectionner un projet et activer Gmail API + Google Calendar API.
3. Configurer l'écran de consentement OAuth. Pour usage personnel, ajouter le compte Google comme utilisateur test si l'application est en mode test.
4. Créer un identifiant OAuth de type Application Web.
5. Ajouter l'origine JavaScript autorisée : https://choaybdc.github.io
6. Copier le Client ID (pas de secret) dans Paramètres de l'application.

Scopes : openid, email, calendar.readonly, calendar.events, gmail.readonly.

## Installation Android
Ouvrir l'URL dans Chrome Android, menu ⋮, puis Installer l'application / Ajouter à l'écran d'accueil.

## Fonctionnalités
- Liste des événements du calendrier principal sur 30 jours.
- Lecture des e-mails étoilés des 365 derniers jours (jusqu'à 30 résultats, 20 détails affichés).
- Préparation manuelle depuis un e-mail, validation humaine obligatoire.
- Création d'événement avec adresse et lien Google Maps dans la description.
- Rappels Google Agenda 3 jours, 2 jours et 1 jour avant.

## Limites
Les appels Google partent du navigateur vers les API Google. Aucun serveur de traitement d'e-mails n'est installé. L'analyse Gmail affiche des messages candidats ; elle ne confirme pas automatiquement les rendez-vous. Les notifications de rappel fiables sont celles de Google Agenda. Le bouton notifications demande l'autorisation navigateur mais ne programme pas de notifications locales en arrière-plan.
