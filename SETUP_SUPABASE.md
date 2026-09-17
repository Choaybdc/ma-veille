# Ma Veille V6 — connexion Supabase

## 1. Configuration du navigateur
Dans `supabase-config.js`, renseignez uniquement :
- `url` = Project URL Supabase
- `anonKey` = Publishable key (ou ancienne clé anon)

Ne mettez jamais une `sb_secret_...` dans le navigateur.

## 2. Base de données
Dans Supabase → SQL Editor, exécutez `supabase_schema.sql`.
Le script V6 est idempotent : les policies existantes sont supprimées/recréées et Realtime est activé pour `settings` et `opportunities`.

## 3. Compte admin
Créez votre utilisateur dans Authentication → Users, puis exécutez :

```sql
insert into public.profiles(id, role)
values ('VOTRE-UUID', 'admin')
on conflict (id) do update set role='admin';
```

## 4. Synchronisation
- Le client (`index.html`) lit `settings` et `opportunities` depuis Supabase.
- Le dashboard (`admin.html`) écrit dans Supabase après authentification et vérification du rôle admin.
- Supabase Realtime informe automatiquement les pages ouvertes lorsqu'une donnée change.
- L'application actualise aussi les données lorsqu'elle revient au premier plan ou retrouve Internet.
- Le service worker V6 utilise une stratégie network-first pour les pages HTML afin d'éviter de conserver une ancienne version du site.

## 5. GitHub Pages
Après modification de `supabase-config.js`, envoyez les fichiers V6 dans le dépôt GitHub et attendez le déploiement Pages.

## 6. Test recommandé
1. Ouvrez Ma Veille sur l'ordinateur.
2. Ouvrez aussi Ma Veille sur le téléphone.
3. Connectez-vous à `admin.html` sur l'ordinateur.
4. Ajoutez/modifiez une opportunité.
5. Le téléphone doit recevoir la modification automatiquement si la page est ouverte et Realtime est actif.
6. Si le téléphone était hors ligne, rouvrez l'application ou utilisez `Actualiser` lorsqu'il retrouve Internet.
