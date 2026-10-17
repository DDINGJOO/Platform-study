-- A: 1편과 같은 "없으면 넣고, 그 행을 잠근다"
DROP TABLE IF EXISTS visit;
CREATE TABLE visit (
  id       BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_key VARCHAR(32) NOT NULL,
  cnt      INT NOT NULL DEFAULT 0,
  UNIQUE KEY uk_user_key (user_key)
) ENGINE=InnoDB;

-- B: 두 행을 서로 반대 순서로 갱신한다 / C: 갭 잠금 표기 확인용
DROP TABLE IF EXISTS acct;
CREATE TABLE acct (
  id  INT PRIMARY KEY,
  bal INT NOT NULL
) ENGINE=InnoDB;
INSERT INTO acct VALUES (1, 100), (2, 100), (10, 100);
