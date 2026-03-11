-- PropertyAdvisor schema v1
-- Practical first-pass Postgres schema for residential property advisory.

create extension if not exists pgcrypto;

create table if not exists suburbs (
  id uuid primary key default gen_random_uuid(),
  country_code text not null default 'AU',
  state_code text,
  suburb_name text not null,
  postcode text,
  latitude numeric(9,6),
  longitude numeric(9,6),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (country_code, state_code, suburb_name, postcode)
);

create table if not exists properties (
  id uuid primary key default gen_random_uuid(),
  suburb_id uuid references suburbs(id),
  address_line_1 text not null,
  address_line_2 text,
  suburb_name text not null,
  state_code text,
  postcode text,
  country_code text not null default 'AU',
  normalized_address text,
  latitude numeric(9,6),
  longitude numeric(9,6),
  property_type text not null,
  bedrooms integer,
  bathrooms numeric(4,1),
  parking_spaces integer,
  land_area_sqm numeric(10,2),
  building_area_sqm numeric(10,2),
  year_built integer,
  source_confidence text not null default 'medium',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_properties_suburb_id on properties(suburb_id);
create index if not exists idx_properties_normalized_address on properties(normalized_address);
create index if not exists idx_properties_type on properties(property_type);

create table if not exists listings (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references properties(id) on delete cascade,
  source_name text not null,
  source_listing_id text not null,
  listing_type text not null, -- sale | rent
  status text not null, -- active | under_offer | withdrawn | sold | leased | expired
  listing_url text,
  first_seen_at timestamptz,
  last_seen_at timestamptz,
  listed_at timestamptz,
  off_market_at timestamptz,
  asking_price numeric(14,2),
  asking_price_text text,
  rent_price_weekly numeric(12,2),
  headline text,
  description text,
  agent_name text,
  agency_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (source_name, source_listing_id)
);

create index if not exists idx_listings_property_id on listings(property_id);
create index if not exists idx_listings_status on listings(status);
create index if not exists idx_listings_type_status on listings(listing_type, status);

create table if not exists listing_snapshots (
  id uuid primary key default gen_random_uuid(),
  listing_id uuid not null references listings(id) on delete cascade,
  observed_at timestamptz not null default now(),
  status text not null,
  asking_price numeric(14,2),
  asking_price_text text,
  rent_price_weekly numeric(12,2),
  headline text,
  description text,
  days_on_market integer,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_listing_snapshots_listing_id on listing_snapshots(listing_id);
create index if not exists idx_listing_snapshots_observed_at on listing_snapshots(observed_at desc);

create table if not exists sales_events (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references properties(id) on delete cascade,
  listing_id uuid references listings(id) on delete set null,
  sale_date date not null,
  sale_price numeric(14,2),
  sale_method text,
  days_on_market integer,
  vendor_discount_pct numeric(6,3),
  is_auction boolean,
  source_name text,
  source_event_id text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (source_name, source_event_id)
);

create index if not exists idx_sales_events_property_id on sales_events(property_id);
create index if not exists idx_sales_events_sale_date on sales_events(sale_date desc);

create table if not exists rental_events (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references properties(id) on delete cascade,
  listing_id uuid references listings(id) on delete set null,
  lease_date date,
  weekly_rent numeric(12,2),
  days_on_market integer,
  source_name text,
  source_event_id text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (source_name, source_event_id)
);

create index if not exists idx_rental_events_property_id on rental_events(property_id);
create index if not exists idx_rental_events_lease_date on rental_events(lease_date desc);

create table if not exists market_metrics (
  id uuid primary key default gen_random_uuid(),
  suburb_id uuid not null references suburbs(id) on delete cascade,
  metric_period text not null, -- weekly | monthly | quarterly
  period_start date not null,
  period_end date not null,
  property_type text,
  median_sale_price numeric(14,2),
  median_weekly_rent numeric(12,2),
  sales_count integer,
  rentals_count integer,
  new_listing_count integer,
  active_listing_count integer,
  avg_days_on_market numeric(10,2),
  avg_vendor_discount_pct numeric(6,3),
  gross_yield_pct numeric(6,3),
  price_growth_pct numeric(7,3),
  rent_growth_pct numeric(7,3),
  demand_score numeric(8,3),
  supply_score numeric(8,3),
  market_temperature text, -- cold | balanced | warm | hot
  created_at timestamptz not null default now(),
  unique (suburb_id, metric_period, period_start, property_type)
);

create index if not exists idx_market_metrics_suburb_period on market_metrics(suburb_id, metric_period, period_start desc);

create table if not exists comparable_sets (
  id uuid primary key default gen_random_uuid(),
  target_property_id uuid not null references properties(id) on delete cascade,
  purpose text not null, -- buy_eval | sell_eval | rent_eval
  basis text not null, -- sales | listings | rentals | mixed
  status text not null default 'complete',
  generated_at timestamptz not null default now(),
  algorithm_version text not null default 'v1',
  quality_score numeric(8,3),
  notes text,
  created_at timestamptz not null default now()
);

create index if not exists idx_comparable_sets_target_property_id on comparable_sets(target_property_id, generated_at desc);

create table if not exists comparable_members (
  id uuid primary key default gen_random_uuid(),
  comparable_set_id uuid not null references comparable_sets(id) on delete cascade,
  comparable_property_id uuid not null references properties(id) on delete cascade,
  sale_event_id uuid references sales_events(id) on delete set null,
  listing_id uuid references listings(id) on delete set null,
  rental_event_id uuid references rental_events(id) on delete set null,
  rank_order integer not null,
  similarity_score numeric(8,3),
  distance_km numeric(8,3),
  price_delta_pct numeric(8,3),
  feature_summary text,
  rationale text,
  created_at timestamptz not null default now(),
  unique (comparable_set_id, rank_order)
);

create index if not exists idx_comparable_members_set_id on comparable_members(comparable_set_id);
create index if not exists idx_comparable_members_property_id on comparable_members(comparable_property_id);

create table if not exists property_advice_snapshots (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references properties(id) on delete cascade,
  comparable_set_id uuid references comparable_sets(id) on delete set null,
  market_metrics_id uuid references market_metrics(id) on delete set null,
  generated_at timestamptz not null default now(),
  advisory_context text not null, -- buyer | seller | investor
  recommendation text not null,
  confidence text not null, -- low | medium | high
  target_value_low numeric(14,2),
  target_value_high numeric(14,2),
  estimated_rent_weekly numeric(12,2),
  headline_summary text,
  rationale jsonb not null default '[]'::jsonb,
  risks jsonb not null default '[]'::jsonb,
  metrics jsonb not null default '{}'::jsonb,
  algorithm_version text not null default 'v1',
  created_at timestamptz not null default now()
);

create index if not exists idx_property_advice_snapshots_property_id on property_advice_snapshots(property_id, generated_at desc);

create table if not exists watchlists (
  id uuid primary key default gen_random_uuid(),
  user_ref text not null,
  name text not null,
  description text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists idx_watchlists_user_ref_name on watchlists(user_ref, name);

create table if not exists alert_rules (
  id uuid primary key default gen_random_uuid(),
  watchlist_id uuid not null references watchlists(id) on delete cascade,
  property_id uuid references properties(id) on delete cascade,
  suburb_id uuid references suburbs(id) on delete cascade,
  rule_type text not null, -- price_change | new_sale_comp | listing_status_change | advice_change | market_shift
  is_active boolean not null default true,
  threshold_numeric numeric(14,4),
  threshold_text text,
  last_triggered_at timestamptz,
  delivery_channel text default 'in_app',
  config jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (
    (property_id is not null) or (suburb_id is not null)
  )
);

create index if not exists idx_alert_rules_watchlist_id on alert_rules(watchlist_id);
create index if not exists idx_alert_rules_active on alert_rules(is_active);

comment on table properties is 'Canonical residential property records.';
comment on table listings is 'External listing records linked to canonical properties.';
comment on table listing_snapshots is 'Observed listing states over time for price/status history.';
comment on table sales_events is 'Property sale history used for comparables and market metrics.';
comment on table rental_events is 'Property rental/lease history used for rental comps and yield signals.';
comment on table market_metrics is 'Suburb-level periodic market intelligence aggregates.';
comment on table comparable_sets is 'Generated comparable result groups for a target property and purpose.';
comment on table property_advice_snapshots is 'Historical recommendation snapshots for auditability.';
