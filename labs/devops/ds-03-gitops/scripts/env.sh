# 공통 변수. 다른 스크립트가 source 한다.
export CTX=kind-ds-03
export ARGOCD_VERSION=v3.5.4
export GITEA_URL=http://localhost:26030
export GITEA_USER=lab
export GITEA_PASS=lab-password-123   # 실습용 계정. 클러스터를 지우면 같이 사라진다
export LAB_EMAIL="lab@""example.com"   # 실습용 주소(예약 도메인). 마스킹 검사에 걸리지 않게 나눠 적었다
export WORK=${DS03_WORK:-/tmp/ds-03-work}   # 저장소 밖에 만드는 git 작업 사본
k() { kubectl --context "$CTX" "$@"; }
