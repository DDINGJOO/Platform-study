insert into stock (sku, available) values ('A-100', 50), ('B-200', 0), ('C-300', 1000) on conflict (sku) do nothing;
