# 서비스 하나의 이미지. 빌드 컨텍스트는 실습 디렉터리(../) 다: app/ 과 repo/(스타터 파일 저장소)를 쓴다.
# SVC 를 RUN 에 써서 서비스마다 캐시 사슬이 갈리게 한다(다섯 저장소가 각자 빌드하는 셈).
# Gradle 의존성 캐시는 BuildKit 캐시로 공유한다(CI 의 의존성 캐시에 해당).
FROM gradle:9.8.1-jdk21 AS build
ARG SVC=svc
ARG STARTER_VERSION=1.0.0
ARG BUILD_ID=0
RUN echo "$SVC starter=$STARTER_VERSION build=$BUILD_ID" > /build-id
WORKDIR /src
COPY app/settings.gradle app/build.gradle ./
COPY app/src ./src
COPY repo /repo
RUN --mount=type=cache,target=/root/.gradle-cache \
    GRADLE_USER_HOME=/root/.gradle-cache gradle bootJar --no-daemon -q -PstarterVersion=$STARTER_VERSION

FROM eclipse-temurin:21-jre
COPY --from=build /build-id /build-id
COPY --from=build /src/build/libs/svc.jar /app/svc.jar
ENTRYPOINT ["java", "-jar", "/app/svc.jar"]
