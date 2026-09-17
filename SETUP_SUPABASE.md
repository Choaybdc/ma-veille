# Ma Veille V5 — activation de l'administration sécurisée

Cette version conserve un mode statique de secours, mais peut fonctionner avec Supabase pour une vraie séparation client/admin.

## 1. Créer le projet
1. Créez un projet sur Supabase.
2. Dans SQL Editor, exécutez `supabase_schema.sql`.
3. Dans Authentication > Users, créez votre compte administrateur.
4. Copiez son UUID et exécutez la dernière commande commentée du SQL en remplaçant `VOTRE-UUID`.

## 2. Connecter l'application
Dans `supabase-config.js`, renseignez :
- `url` = Project URL
- `anonKey` = Publishable/anon key

Ne mettez JAMAIS une `service_role` key dans le navigateur.

## 3. Publier
Envoyez les fichiers du ZIP sur votre dépôt GitHub Pages.

## 4. Fonctionnement
- Client : lit les opportunités et les réglages publics depuis Supabase.
- Admin : se connecte avec email + mot de passe.
- Seul un profil `admin` peut créer, modifier ou supprimer les données grâce aux RLS.
- Sans configuration Supabase, l'application revient au mode `veille.json` + stockage local.

## 5. Prochaine étape commerciale
Pour les abonnements Premium, ajoutez ensuite Stripe + une table `subscriptions` côté serveur/Edge Function. Ne mettez jamais la clé secrète Stripe dans le navigateur.
