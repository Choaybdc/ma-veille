-- Ma Veille V6 — schéma Supabase idempotent
-- Peut être relancé sans erreur si les tables/policies existent déjà.

create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  role text not null default 'user' check (role in ('user','admin')),
  created_at timestamptz not null default now()
);

create table if not exists public.settings (
  id integer primary key default 1 check (id = 1),
  title text not null default '🔎 Ma Veille',
  subtitle text not null default 'Trouvez rapidement les opportunités qui vous intéressent.',
  accent text not null default '#111827',
  radius integer not null default 16,
  footer text not null default 'Ma Veille · Votre tableau de bord d’opportunités',
  updated_at timestamptz not null default now()
);

create table if not exists public.opportunities (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  organization text,
  url text,
  conditions text,
  category text not null default 'cdi',
  location text,
  published_at date,
  deadline date,
  is_new boolean not null default true,
  is_open boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

insert into public.settings(id) values (1) on conflict (id) do nothing;

create or replace function public.is_admin()
returns boolean
language sql stable security definer set search_path = public
as $$
  select exists (
    select 1 from public.profiles
    where id = auth.uid() and role = 'admin'
  );
$$;

alter table public.profiles enable row level security;
alter table public.settings enable row level security;
alter table public.opportunities enable row level security;

-- Policies idempotentes : suppression puis recréation pour éviter l'erreur 42710.
drop policy if exists "public can read settings" on public.settings;
drop policy if exists "admins manage settings" on public.settings;
drop policy if exists "public can read opportunities" on public.opportunities;
drop policy if exists "admins manage opportunities" on public.opportunities;
drop policy if exists "users read own profile" on public.profiles;

create policy "public can read settings"
on public.settings for select using (true);

create policy "admins manage settings"
on public.settings for all using (public.is_admin()) with check (public.is_admin());

create policy "public can read opportunities"
on public.opportunities for select using (true);

create policy "admins manage opportunities"
on public.opportunities for all using (public.is_admin()) with check (public.is_admin());

create policy "users read own profile"
on public.profiles for select using (auth.uid() = id);

-- Active Realtime pour les deux tables. Le bloc est idempotent.
do $$
begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime'
      and schemaname = 'public'
      and tablename = 'settings'
  ) then
    alter publication supabase_realtime add table public.settings;
  end if;
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime'
      and schemaname = 'public'
      and tablename = 'opportunities'
  ) then
    alter publication supabase_realtime add table public.opportunities;
  end if;
end $$;

-- Après création de votre compte dans Authentication > Users, attribuez le rôle admin :
-- insert into public.profiles(id, role)
-- values ('VOTRE-UUID', 'admin')
-- on conflict (id) do update set role = 'admin';
