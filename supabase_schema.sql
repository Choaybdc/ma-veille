-- Ma Veille — schéma Supabase
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

alter table public.profiles enable row level security;
alter table public.settings enable row level security;
alter table public.opportunities enable row level security;

create or replace function public.is_admin()
returns boolean language sql stable security definer set search_path = public
as $$ select exists(select 1 from public.profiles where id = auth.uid() and role = 'admin'); $$;

create policy "public can read settings" on public.settings for select using (true);
create policy "admins manage settings" on public.settings for all using (public.is_admin()) with check (public.is_admin());
create policy "public can read opportunities" on public.opportunities for select using (true);
create policy "admins manage opportunities" on public.opportunities for all using (public.is_admin()) with check (public.is_admin());
create policy "users read own profile" on public.profiles for select using (auth.uid() = id);

-- Après avoir créé votre compte dans Authentication > Users, remplacez l'UUID ci-dessous :
-- insert into public.profiles(id, role) values ('VOTRE-UUID', 'admin') on conflict (id) do update set role='admin';
