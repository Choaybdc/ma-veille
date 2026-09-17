# Ma Veille V6 — synchronisation Supabase complète

Ma Veille V6 sépare :
- `index.html` : surface client/public ;
- `admin.html` : back-office administrateur ;
- Supabase : authentification, PostgreSQL, RLS et Realtime.

## Synchronisation
Les opportunités et réglages ne dépendent plus du `localStorage` en production. Le dashboard écrit dans Supabase et le client lit Supabase. Les changements sont propagés par Realtime aux pages ouvertes.

## Sécurité
Le navigateur utilise uniquement la clé publique Supabase. Les écritures sont protégées par RLS et par le rôle `admin` dans `profiles`.

## À faire une seule fois
1. Configurer `supabase-config.js`.
2. Exécuter `supabase_schema.sql`.
3. Créer le compte Supabase.
4. Lui attribuer le rôle `admin`.
5. Déployer les fichiers sur GitHub Pages.

## Limites actuelles
Cette version n'inclut pas encore les comptes clients, favoris multi-appareils, notifications push, abonnement Premium ou Stripe. Ces fonctionnalités peuvent être ajoutées ensuite.
