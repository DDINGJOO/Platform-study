create table if not exists payments (order_id varchar(64) primary key, sku varchar(32), qty int, paid_at timestamp);
