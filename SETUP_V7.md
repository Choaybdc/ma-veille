# Ma Veille V7 — surveillance automatique

V7 ajoute un vrai **collector serveur**. Le navigateur n'a pas besoin d'être ouvert : Supabase Cron appelle l'Edge Function, qui interroge France Travail, déduplique les offres et les écrit dans Supabase. Ma Veille reçoit ensuite les nouvelles lignes via Supabase Realtime.

## Ce qui est déjà préparé
- Edge Function : `supabase/functions/sync-opportunities/index.ts`
- Source initiale : **France Travail – API Offres d'emploi v2**
- fenêtre de recherche configurable
- recherche par mots-clés
- déduplication `source + external_id`
- classification automatique
- journal des exécutions dans `monitoring_runs`
- exécution Cron toutes les minutes
- bouton **Lancer maintenant** réservé à l'administrateur

France Travail indique que son API Offres d'emploi permet de restituer les offres actives en temps réel et que leur réutilisation passe par une licence API partenaire. citeturn0search1

## 1. Obtenir les identifiants France Travail
Sur `francetravail.io`, créez une application et abonnez-la à l'API **Offres d'emploi v2**. L'authentification utilise OAuth2 client credentials. Les identifiants restent des secrets : **ne les mettez jamais dans GitHub ni dans `supabase-config.js`**. citeturn2search0turn0search1

## 2. Déployer l'Edge Function
Dans votre projet Supabase, déployez le dossier :

`supabase/functions/sync-opportunities/index.ts`

Si vous utilisez la CLI Supabase :

```bash
supabase functions deploy sync-opportunities
```

## 3. Ajouter les secrets de la fonction
Dans **Supabase → Edge Functions → Secrets**, ajoutez :

- `FRANCE_TRAVAIL_CLIENT_ID` = votre Client ID
- `FRANCE_TRAVAIL_CLIENT_SECRET` = votre Client Secret
- `MA_VEILLE_CRON_SECRET` = une longue valeur aléatoire que vous choisissez

`SUPABASE_URL` et `SUPABASE_SERVICE_ROLE_KEY` sont normalement fournis automatiquement à l'Edge Function par Supabase. **Ne publiez jamais le service-role key dans GitHub.**

## 4. Exécuter le SQL V7
Dans **Supabase → SQL Editor**, exécutez `supabase_schema_v7.sql`.

Le script crée notamment :
- `monitoring_settings`
- `monitoring_runs`
- les colonnes `source`, `external_id`, `imported_at`
- la déduplication
- Realtime
- le Cron

## 5. Configurer le Cron
Dans Supabase Vault, créez ces trois secrets :

- `project_url` = URL de votre projet Supabase
- `publishable_key` = clé publishable/anon
- `ma_veille_cron_secret` = exactement la même valeur que `MA_VEILLE_CRON_SECRET`

Puis exécutez le bloc Cron présent à la fin de `supabase_schema_v7.sql`.

Il lance la fonction toutes les minutes (`* * * * *`).

## 6. Tester
1. Ouvrez **Ma Veille → Administration**.
2. Connectez-vous avec votre compte admin.
3. Dans **Surveillance automatique**, vérifiez les mots-clés.
4. Cliquez **⚡ Lancer maintenant**.
5. Vérifiez `monitoring_runs` et `opportunities` dans Supabase.
6. Ouvrez Ma Veille sur un autre appareil : une nouvelle offre doit apparaître via Realtime.

## 7. Ajouter les autres sources
La V7 est conçue pour ajouter d'autres adaptateurs séparés :
- Indeed
- HelloWork
- Monster
- APEC
- Welcome to the Jungle
- sources universitaires / recherche

Pour chacune, Ma Veille doit utiliser une API, un flux ou une intégration autorisée par le fournisseur, plutôt qu'un scraping non autorisé.
