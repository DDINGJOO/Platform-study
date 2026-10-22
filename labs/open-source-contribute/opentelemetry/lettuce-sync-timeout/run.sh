#!/bin/zsh
# usage: run.sh <logname> <extra gradle args...>
cd ${OTEL_CLONE}
name=$1; shift
start=$(date +%s)
JAVA_HOME=$(/usr/libexec/java_home -v 25) ./gradlew --no-daemon --max-workers=2 -Dorg.gradle.jvmargs=-Xmx2g -Ddev=true "$@" > ${LOGDIR}/${name}.log 2>&1
echo "exit=$? elapsed=$(( $(date +%s) - start ))s" >> ${LOGDIR}/${name}.log
