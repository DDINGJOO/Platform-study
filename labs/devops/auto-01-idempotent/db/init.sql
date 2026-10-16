-- 절차서 시절 그대로의 테이블: 이름에 UNIQUE 제약이 없다.
-- 멱등 스크립트(ops/idem.sh)는 실행할 때 UNIQUE 인덱스를 스스로 만든다.
CREATE TABLE tenants (
  id         serial PRIMARY KEY,
  name       text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
