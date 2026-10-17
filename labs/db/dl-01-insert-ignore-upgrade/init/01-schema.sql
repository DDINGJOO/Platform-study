-- 회원별 "첫 방문" 행. 같은 회원은 한 행만 생겨야 한다. 같은 뜻의 테이블을 키 구조만 달리해 둘 둔다.

-- (가) 흔한 모양: 대리 키(AUTO_INCREMENT) + member_id 보조 유니크 키
CREATE TABLE lab.first_visit (
  id          BIGINT AUTO_INCREMENT PRIMARY KEY,
  member_id   BIGINT NOT NULL,
  visit_count INT    NOT NULL DEFAULT 1,
  UNIQUE KEY uk_member (member_id)
) ENGINE = InnoDB;

-- (나) member_id 자체가 기본 키
CREATE TABLE lab.first_visit_pk (
  member_id   BIGINT NOT NULL PRIMARY KEY,
  visit_count INT    NOT NULL DEFAULT 1
) ENGINE = InnoDB;
