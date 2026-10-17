-- 처음 상태: 평문만 들어 있던 운영 테이블을 흉내 낸다.
-- rrn 은 주민번호 형식의 가짜 값이다(생년월일 자리가 000000 이라 실존할 수 없다).
-- 길이는 평문에 맞춘 VARCHAR(20). 암호문은 이보다 길어서 0단계에서 넓혀야 한다.
DROP TABLE IF EXISTS agent;
DROP TABLE IF EXISTS batch_state;
CREATE TABLE agent (
  id         BIGINT      NOT NULL PRIMARY KEY,
  name       VARCHAR(30) NOT NULL,
  rrn        VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin NULL,
  last_login DATETIME(6) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 채우기·복원 배치의 진행 위치. 행이 있으면 그 자리부터 이어서 돈다.
CREATE TABLE batch_state (
  job        VARCHAR(20) NOT NULL PRIMARY KEY,
  cursor_id  BIGINT      NOT NULL,
  updated_at DATETIME(6) NOT NULL
) ENGINE=InnoDB;
