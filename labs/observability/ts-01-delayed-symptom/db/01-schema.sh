#!/bin/sh
# 주문 테이블과 인덱스, 시작 데이터. SEED_ROWS 행을 고객 1만 명에게 고르게 나눠 넣는다.
set -e
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<SQL
create table orders (
  id          bigserial primary key,
  customer_ref varchar(16)   not null,
  amount      numeric(10,2) not null,
  created_at  timestamptz   not null default now()
);
create index orders_customer_created on orders (customer_ref, created_at desc);
insert into orders (customer_ref, amount, created_at)
select 'C' || lpad(floor(random() * 10000)::int::text, 5, '0'),
       round((random() * 100)::numeric, 2),
       now() - random() * interval '30 days'
from generate_series(1, ${SEED_ROWS:-50000});
analyze orders;
SQL
