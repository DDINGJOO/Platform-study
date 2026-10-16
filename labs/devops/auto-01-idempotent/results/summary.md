# 실습-1 요약 (scripts/summarize.py 가 out/ 에서 만든다)

## e2 같은 고객사를 동시에 두 번

| 변형 | 시행 | 중복 행이 생긴 시행 | 중복 location 이 생긴 시행 | nginx 가 내려간 채 끝난 시행 | 경로 누락 시행 | 불일치 합 |
|---|---|---|---|---|---|---|
| naive | 20 | 20 | 20 | 1 | 20 | 61 |
| idem LOCK=0 | 20 | 0 | 0 | 0 | 0 | 0 |
| idem LOCK=1 | 20 | 0 | 0 | 0 | 0 | 0 |

## e2b 다른 고객사 둘(t1, t2)을 동시에

| 변형 | 시행 | 중복 행이 생긴 시행 | 중복 location 이 생긴 시행 | nginx 가 내려간 채 끝난 시행 | 경로 누락 시행 | 불일치 합 |
|---|---|---|---|---|---|---|
| naive | 20 | 0 | 0 | 0 | 0 | 0 |
| idem LOCK=0 | 20 | 0 | 0 | 0 | 0 | 0 |
| idem LOCK=1 | 20 | 0 | 0 | 0 | 0 | 0 |

## e3 부하(초당 100건 + 1초짜리 요청 4개 동시) 중 설정 반영

| 변형 | 시행 | 빠른 요청 | 실패 | 1초 요청 | 실패 | 실패 구간(초) | 반영 소요(초) | 실패 종류 |
|---|---|---|---|---|---|---|---|---|
| naive | 1 | 2000 | 6 | 151 | 71 | 0.808 | 0.074 | {'RemoteDisconnected': 4, 'ConnectionResetError': 9, 'ConnectionRefusedError': 64} |
| naive | 2 | 2000 | 5 | 127 | 47 | 0.857 | 0.077 | {'RemoteDisconnected': 4, 'ConnectionResetError': 8, 'ConnectionRefusedError': 40} |
| naive | 3 | 2000 | 5 | 104 | 24 | 0.828 | 0.075 | {'RemoteDisconnected': 4, 'ConnectionResetError': 4, 'ConnectionRefusedError': 21} |
| naive | 4 | 2000 | 6 | 148 | 68 | 0.823 | 0.079 | {'RemoteDisconnected': 4, 'ConnectionResetError': 6, 'ConnectionRefusedError': 64} |
| naive | 5 | 2000 | 8 | 193 | 113 | 0.829 | 0.097 | {'RemoteDisconnected': 4, 'ConnectionResetError': 6, 'ConnectionRefusedError': 111} |
| idem | 1 | 2000 | 0 | 80 | 0 | 0.000 | 0.240 | {} |
| idem | 2 | 2000 | 0 | 80 | 0 | 0.000 | 0.145 | {} |
| idem | 3 | 2000 | 0 | 80 | 0 | 0.000 | 0.141 | {} |
| idem | 4 | 2000 | 0 | 80 | 0 | 0.000 | 0.140 | {} |
| idem | 5 | 2000 | 0 | 80 | 0 | 0.000 | 0.249 | {} |

## e3b 틀린 설정(중복 location)을 반영할 때

| 변형 | stop 종료 코드 | stop 대기 10초 초과 | 시작/reload 종료 코드 | 반영 뒤 nginx 프로세스 수 | 빠른 요청 | 실패 | 1초 요청 | 실패 | 첫 실패(반영 시작 기준 초) | 실패 구간(초) | 실패 종류 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| stopstart | 1 | 1 | 1 | 16 | 2000 | 0 | 80 | 0 | None | 0.000 | {} |
| reload | - | 0 | 1 | 16 | 2000 | 0 | 80 | 0 | None | 0.000 | {} |
| killstart | 0 | 0 | 1 | 0 | 2000 | 1223 | 186622 | 186594 | -0.745 | 12.976 | {'RemoteDisconnected': 4, 'ConnectionResetError': 5, 'ConnectionRefusedError': 187808} |

## e4 중간에 끊고 다시 돌리기

| 변형 | 끊은 지점 | 끊긴 직후 불일치 | 다시 돌린 뒤 불일치 | 다시 돌린 결과 |
|---|---|---|---|---|
| naive | after_db | rows=2 dup_rows=0 locations=1 dup_locations=0 missing_routes=1 orphan_routes=0 nginx_up=1 mismatch=1 | rows=2 dup_rows=0 locations=1 dup_locations=0 missing_routes=1 orphan_routes=0 nginx_up=1 mismatch=1 | [naive] t1 already exists |
| naive | after_conf | rows=2 dup_rows=0 locations=2 dup_locations=0 missing_routes=1 orphan_routes=0 nginx_up=1 mismatch=1 | rows=2 dup_rows=0 locations=2 dup_locations=0 missing_routes=1 orphan_routes=0 nginx_up=1 mismatch=1 | [naive] t1 already exists |
| idem APPLIED=file | after_db | rows=2 dup_rows=0 locations=1 dup_locations=0 missing_routes=1 orphan_routes=0 nginx_up=1 mismatch=1 | rows=2 dup_rows=0 locations=2 dup_locations=0 missing_routes=0 orphan_routes=0 nginx_up=1 mismatch=0 | 2026/10/16 04:30:12 [notice] 61906#61906: signal process started|[idem] t1 ok (changed=1) |
| idem APPLIED=file | after_conf | rows=2 dup_rows=0 locations=2 dup_locations=0 missing_routes=1 orphan_routes=0 nginx_up=1 mismatch=1 | rows=2 dup_rows=0 locations=2 dup_locations=0 missing_routes=1 orphan_routes=0 nginx_up=1 mismatch=1 | [idem] 확인 실패: /t/t1/ 가 404 |
| idem APPLIED=file | after_reload | rows=2 dup_rows=0 locations=2 dup_locations=0 missing_routes=0 orphan_routes=0 nginx_up=1 mismatch=0 | rows=2 dup_rows=0 locations=2 dup_locations=0 missing_routes=0 orphan_routes=0 nginx_up=1 mismatch=0 | [idem] t1 ok (changed=0) |
| idem | after_db | rows=2 dup_rows=0 locations=1 dup_locations=0 missing_routes=1 orphan_routes=0 nginx_up=1 mismatch=1 | rows=2 dup_rows=0 locations=2 dup_locations=0 missing_routes=0 orphan_routes=0 nginx_up=1 mismatch=0 | 2026/10/16 04:30:25 [notice] 62414#62414: signal process started|[idem] t1 ok (changed=1) |
| idem | after_conf | rows=2 dup_rows=0 locations=2 dup_locations=0 missing_routes=1 orphan_routes=0 nginx_up=1 mismatch=1 | rows=2 dup_rows=0 locations=2 dup_locations=0 missing_routes=0 orphan_routes=0 nginx_up=1 mismatch=0 | 2026/10/16 04:30:28 [notice] 62560#62560: signal process started|[idem] t1 ok (changed=1) |
| idem | after_reload | rows=2 dup_rows=0 locations=2 dup_locations=0 missing_routes=0 orphan_routes=0 nginx_up=1 mismatch=0 | rows=2 dup_rows=0 locations=2 dup_locations=0 missing_routes=0 orphan_routes=0 nginx_up=1 mismatch=0 | [idem] t1 ok (changed=0) |
