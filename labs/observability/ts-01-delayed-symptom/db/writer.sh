#!/bin/sh
# 주문이 계속 쌓인다. 1초마다 WRITE_ROWS 행을 넣는다(실제 속도는 insert 시간만큼 조금 느리다).
until pg_isready -q -h db -U shop -d shop; do sleep 1; done
while true; do
  psql -q -h db -U shop -d shop -c "insert into orders (customer_ref, amount)
    select 'C' || lpad(floor(random() * 10000)::int::text, 5, '0'), round((random() * 100)::numeric, 2)
    from generate_series(1, ${WRITE_ROWS:-250})" > /dev/null
  sleep 1
done
