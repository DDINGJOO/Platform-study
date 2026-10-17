-- 본 테이블(agent)에서 두 COUNT 를 나란히 센다
SELECT SUM(rrn REGEXP '^[0-9]{6}-?[0-9]{7}$')            AS plain_shape,
       SUM(rrn IS NOT NULL AND rrn NOT LIKE 'LABENC1:%')  AS not_cipher,
       SUM(rrn <> '' AND rrn NOT LIKE 'LABENC1:%')        AS not_cipher_ne_empty,
       SUM(rrn IS NULL)                                   AS nulls,
       COUNT(*)                                           AS total
FROM agent;
