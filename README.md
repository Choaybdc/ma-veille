# Ma Veille V5 — Client + Admin sécurisé

## Ce qui est nouveau
- `index.html` : surface publique/client.
- `admin.html` : back-office administrateur séparé.
- `supabase-config.js` : connexion optionnelle à Supabase.
- `supabase_schema.sql` : base de données + authentification + RLS.
- `SETUP_SUPABASE.md` : procédure de mise en ligne.

## Mode production
Avec Supabase configuré :
- les opportunités et l'apparence sont stockées dans la base ;
- l'admin se connecte par email/mot de passe ;
- les règles RLS empêchent un utilisateur non admin de modifier les données ;
- le client lit les données en temps réel lors de l'actualisation.

Sans Supabase, le projet garde un mode statique de secours avec `veille.json` et `localStorage`.

## Important
GitHub Pages reste l'hébergement du front-end. Les secrets serveur ne doivent jamais être placés dans le navigateur. Utilisez uniquement la clé publique Supabase (anon/publishable) côté client et laissez les RLS protéger les données.

## Monétisation
Cette V5 prépare l'architecture pour ajouter ensuite comptes utilisateurs, Premium et paiements Stripe. Stripe n'est pas activé dans cette archive.
