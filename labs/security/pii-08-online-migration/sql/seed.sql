-- 300,000 행. 대부분은 정상 모양 평문이고, 섞여 있는 이상한 값은 운영 테이블에서 흔히 보는 종류다.
--   id % 500 = 0  : 이상한 값 6종을 100 행씩 (뒤에 문자, 자릿수 틀림, 전각 숫자, 빈 문자열, 공백 한 칸, 뒤 공백)
--   id % 997 = 0  : NULL
SET SESSION cte_max_recursion_depth = 1000;
INSERT INTO agent (id, name, rrn)
WITH d AS (SELECT 0 n UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
           UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9),
     seq AS (SELECT 1 + a.n + b.n*10 + c.n*100 + e.n*1000 + f.n*10000 + g.n*100000 AS id
             FROM d a, d b, d c, d e, d f, d g)
SELECT id,
       CONCAT('agent-', id),
       CASE
         WHEN id % 500 = 0 THEN
           CASE (id DIV 500) % 6
             WHEN 0 THEN CONCAT('000000-', LPAD(id, 7, '0'), 'a')
             WHEN 1 THEN CONCAT('000000-', LPAD(id % 1000000, 6, '0'))
             WHEN 2 THEN CONCAT('００００００-',
                          REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                            LPAD(id, 7, '0'),
                          '0','０'),'1','１'),'2','２'),'3','３'),'4','４'),'5','５'),'6','６'),'7','７'),'8','８'),'9','９'))
             WHEN 3 THEN ''
             WHEN 4 THEN ' '
             ELSE CONCAT('000000-', LPAD(id, 7, '0'), ' ')
           END
         WHEN id % 997 = 0 THEN NULL
         ELSE CONCAT('000000-', LPAD(id, 7, '0'))
       END
FROM seq WHERE id <= 300000;
