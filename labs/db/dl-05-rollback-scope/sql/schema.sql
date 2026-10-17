-- 잠글 행 두 개(item)와, 트랜잭션 안에서 "앞 문장"으로 남기는 기록(note)
CREATE TABLE item (id INT PRIMARY KEY, v INT NOT NULL);
CREATE TABLE note (id BIGINT AUTO_INCREMENT PRIMARY KEY, who VARCHAR(40) NOT NULL);
INSERT INTO item VALUES (1, 0), (2, 0);
-- 실습 세션이 information_schema.innodb_trx 로 자기 트랜잭션이 열려 있는지 보려면 PROCESS 가 필요하다
GRANT PROCESS ON *.* TO 'lab'@'%';
