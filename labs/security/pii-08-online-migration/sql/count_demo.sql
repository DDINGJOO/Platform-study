-- 검증 COUNT 를 이상한 값 하나씩으로 비교한다.
-- 같은 값을 두 컬럼에 넣는다. nopad = utf8mb4_0900_bin (NO PAD), pad = utf8mb4_bin (PAD SPACE)
DROP TABLE IF EXISTS count_demo;
CREATE TABLE count_demo (
  kind  VARCHAR(20) NOT NULL,
  nopad VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin NULL,
  pad   VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL
) DEFAULT CHARSET=utf8mb4;
INSERT INTO count_demo (kind, nopad) VALUES
  ('정상',        '000000-0000001'),
  ('하이픈없음',  '0000000000002'),
  ('뒤에문자',    '000000-0000003a'),
  ('자릿수틀림',  '000000-000004'),
  ('전각숫자',    '００００００-０００００05'),
  ('빈문자열',    ''),
  ('공백한칸',    ' '),
  ('뒤공백',      '000000-0000008 '),
  ('NULL',        NULL),
  ('암호문',      'LABENC1:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'),
  ('접두어만',    'LABENC1:hello');
UPDATE count_demo SET pad = nopad;

SELECT '-- 값마다 각 조건에 걸리는가 (1 = 센다)' AS '';
SELECT kind,
       nopad REGEXP '^[0-9]{6}-?[0-9]{7}$'                     AS `평문모양[0-9]`,
       nopad REGEXP '^\\d{6}-?\\d{7}$'                          AS `평문모양\\d`,
       (nopad IS NOT NULL AND nopad NOT LIKE 'LABENC1:%')       AS `암호문아님`,
       (nopad <> '' AND nopad NOT LIKE 'LABENC1:%')             AS `암호문아님(<>'',NOPAD)`,
       (pad   <> '' AND pad   NOT LIKE 'LABENC1:%')             AS `암호문아님(<>'',PAD)`
FROM count_demo;

SELECT '-- 합계' AS '';
SELECT SUM(nopad REGEXP '^[0-9]{6}-?[0-9]{7}$')                          AS `평문모양[0-9]`,
       SUM(nopad REGEXP '^\\d{6}-?\\d{7}$')                               AS `평문모양\\d`,
       SUM(nopad IS NOT NULL AND nopad NOT LIKE 'LABENC1:%')              AS `암호문아님`,
       SUM(nopad <> '' AND nopad NOT LIKE 'LABENC1:%')                    AS `<>'' NOPAD`,
       SUM(pad   <> '' AND pad   NOT LIKE 'LABENC1:%')                    AS `<>'' PAD`,
       SUM(nopad IS NOT NULL AND nopad NOT REGEXP '^LABENC1:[A-Za-z0-9+/]{40,}={0,2}$') AS `엄격형식아님`
FROM count_demo;
