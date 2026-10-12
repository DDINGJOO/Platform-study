# 서비스 공통 런타임 이미지. 빌드는 scripts/lab.py 가 gradle 컨테이너에서 끝내고 jar 만 넣는다.
FROM eclipse-temurin:21-jre
ARG SERVICE
ARG REVISION
LABEL org.opencontainers.image.revision=$REVISION \
      lab.co02.service=$SERVICE
COPY $SERVICE.jar /app/app.jar
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
