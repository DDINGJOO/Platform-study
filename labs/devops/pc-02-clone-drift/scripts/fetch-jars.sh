#!/usr/bin/env bash
# 릴리스된 Spring jar 를 Maven Central 에서 받는다(빌드하지 않는다). demo/*.java 를 돌릴 때 쓴다.
#   WORK=... ./scripts/fetch-jars.sh 6.2.0      -> $WORK/jars/6.2.0/*.jar
set -euo pipefail
WORK=${WORK:?}; V=${1:?spring 버전}
D="$WORK/jars/$V"; mkdir -p "$D"
M=https://repo1.maven.org/maven2
get() { [ -f "$D/$(basename "$1")" ] || curl -sfL -o "$D/$(basename "$1")" "$M/$1"; }
for a in spring-core spring-beans spring-web spring-websocket; do
  get "org/springframework/$a/$V/$a-$V.jar"
done
# spring-jcl 은 6.x 에만 있다. 7.0 의 spring-core pom 은 commons-logging 1.3.5 를 compile 의존성으로 적는다
case "$V" in 6.*) get "org/springframework/spring-jcl/$V/spring-jcl-$V.jar" ;;
  *) get commons-logging/commons-logging/1.3.5/commons-logging-1.3.5.jar ;; esac
# micrometer 1.14.0 은 spring-web 6.2.0 pom 의 compile 의존성 버전. reactor-core 는 optional 이라 3.7.0 을 골랐고,
# 모든 버전에 같은 묶음을 썼다(데모는 Flux.just/collectList 같은 기본 API 만 쓴다)
get io/projectreactor/reactor-core/3.7.0/reactor-core-3.7.0.jar
get org/reactivestreams/reactive-streams/1.0.4/reactive-streams-1.0.4.jar
get io/micrometer/micrometer-observation/1.14.0/micrometer-observation-1.14.0.jar
get io/micrometer/micrometer-commons/1.14.0/micrometer-commons-1.14.0.jar
ls "$D"
