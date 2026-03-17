from __future__ import annotations

"""Market metric derivation and first-pass Postgres rollups."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

import psycopg


def summarize_days_on_market(values: Iterable[int]) -> dict[str, float | int | None]:
    """Produce a simple average-based metric bundle."""

    items = list(values)
    if not items:
        return {"count": 0, "average": None}

    return {
        "count": len(items),
        "average": sum(items) / len(items),
    }


@dataclass(frozen=True)
class MarketMetricsGenerationResult:
    target_slice: str
    suburb_id: str
    metric_period: str
    period_start: date
    period_end: date
    inserted: bool


def generate_suburb_market_metrics(
    *,
    database_url: str,
    suburb_name: str,
    state_code: str,
    postcode: str,
    target_slice: str,
    metric_period: str,
    period_start: date,
    period_end: date,
) -> MarketMetricsGenerationResult:
    """Generate one suburb-level market metric row from persisted source tables.

    The write is idempotent for (suburb_id, metric_period, period_start, property_type=NULL)
    via `on conflict ... do update`.
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id
                from suburbs
                where lower(suburb_name) = lower(%s)
                  and coalesce(upper(state_code), '') = coalesce(upper(%s), '')
                  and coalesce(postcode, '') = coalesce(%s, '')
                order by created_at asc
                limit 1
                """,
                (suburb_name, state_code, postcode),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError(
                    f"suburb not found for metrics generation: {suburb_name}, {state_code} {postcode}"
                )
            suburb_id = row[0]

            cur.execute(
                """
                with listing_scope as (
                  select l.id, l.status, l.first_seen_at, l.last_seen_at
                  from listings l
                  join properties p on p.id = l.property_id
                  where p.suburb_id = %s
                ),
                sale_scope as (
                  select se.sale_price, se.days_on_market, se.vendor_discount_pct
                  from sales_events se
                  join properties p on p.id = se.property_id
                  where p.suburb_id = %s
                    and se.sale_date between %s and %s
                ),
                rental_scope as (
                  select re.weekly_rent, re.days_on_market
                  from rental_events re
                  join properties p on p.id = re.property_id
                  where p.suburb_id = %s
                    and re.lease_date between %s and %s
                ),
                snapshot_scope as (
                  select ls.days_on_market
                  from listing_snapshots ls
                  join listings l on l.id = ls.listing_id
                  join properties p on p.id = l.property_id
                  where p.suburb_id = %s
                    and ls.observed_at::date between %s and %s
                ),
                agg as (
                  select
                    (select percentile_cont(0.5) within group (order by sale_price)
                     from sale_scope where sale_price is not null) as median_sale_price,
                    (select percentile_cont(0.5) within group (order by weekly_rent)
                     from rental_scope where weekly_rent is not null) as median_weekly_rent,
                    (select count(*)::int from sale_scope) as sales_count,
                    (select count(*)::int from rental_scope) as rentals_count,
                    (select count(*)::int from listing_scope where first_seen_at::date between %s and %s) as new_listing_count,
                    (select count(*)::int from listing_scope where status in ('active', 'under_offer') and coalesce(last_seen_at::date, %s) <= %s) as active_listing_count,
                    (
                      select avg(dom_vals.dom)
                      from (
                        select days_on_market::numeric as dom from sale_scope where days_on_market is not null
                        union all
                        select days_on_market::numeric as dom from rental_scope where days_on_market is not null
                        union all
                        select days_on_market::numeric as dom from snapshot_scope where days_on_market is not null
                      ) as dom_vals
                    ) as avg_days_on_market,
                    (select avg(vendor_discount_pct) from sale_scope where vendor_discount_pct is not null) as avg_vendor_discount_pct
                )
                insert into market_metrics (
                  suburb_id, metric_period, period_start, period_end, property_type,
                  median_sale_price, median_weekly_rent,
                  sales_count, rentals_count, new_listing_count, active_listing_count,
                  avg_days_on_market, avg_vendor_discount_pct,
                  gross_yield_pct, demand_score, supply_score, market_temperature
                )
                select
                  %s, %s, %s, %s, null,
                  a.median_sale_price, a.median_weekly_rent,
                  a.sales_count, a.rentals_count, a.new_listing_count, a.active_listing_count,
                  a.avg_days_on_market, a.avg_vendor_discount_pct,
                  case
                    when a.median_sale_price is null or a.median_sale_price = 0 or a.median_weekly_rent is null then null
                    else round(((a.median_weekly_rent * 52.0) / a.median_sale_price) * 100.0, 3)
                  end,
                  least(100.0, greatest(0.0, coalesce(a.rentals_count, 0) * 12.5 + coalesce(a.sales_count, 0) * 8.0)),
                  least(100.0, greatest(0.0, coalesce(a.active_listing_count, 0) * 10.0 + coalesce(a.new_listing_count, 0) * 7.5)),
                  case
                    when coalesce(a.rentals_count, 0) + coalesce(a.sales_count, 0) >= greatest(1, coalesce(a.active_listing_count, 0)) then 'warm'
                    when coalesce(a.active_listing_count, 0) >= 8 then 'cold'
                    else 'balanced'
                  end
                from agg a
                on conflict (suburb_id, metric_period, period_start, property_type)
                do update set
                  period_end = excluded.period_end,
                  median_sale_price = excluded.median_sale_price,
                  median_weekly_rent = excluded.median_weekly_rent,
                  sales_count = excluded.sales_count,
                  rentals_count = excluded.rentals_count,
                  new_listing_count = excluded.new_listing_count,
                  active_listing_count = excluded.active_listing_count,
                  avg_days_on_market = excluded.avg_days_on_market,
                  avg_vendor_discount_pct = excluded.avg_vendor_discount_pct,
                  gross_yield_pct = excluded.gross_yield_pct,
                  demand_score = excluded.demand_score,
                  supply_score = excluded.supply_score,
                  market_temperature = excluded.market_temperature,
                  created_at = now()
                returning (xmax = 0)
                """,
                (
                    suburb_id,
                    suburb_id,
                    period_start,
                    period_end,
                    suburb_id,
                    period_start,
                    period_end,
                    period_start,
                    period_end,
                    period_end,
                    period_end,
                    suburb_id,
                    metric_period,
                    period_start,
                    period_end,
                ),
            )
            inserted = bool(cur.fetchone()[0])
        conn.commit()

    return MarketMetricsGenerationResult(
        target_slice=target_slice,
        suburb_id=suburb_id,
        metric_period=metric_period,
        period_start=period_start,
        period_end=period_end,
        inserted=inserted,
    )
