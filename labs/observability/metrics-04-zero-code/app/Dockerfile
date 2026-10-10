FROM gradle:9-jdk21 AS build
WORKDIR /src
COPY settings.gradle build.gradle ./
COPY src ./src
RUN gradle bootJar --no-daemon -q

FROM eclipse-temurin:21-jre
ARG PYROSCOPE_AGENT_VERSION=2.9.2
ADD https://github.com/grafana/pyroscope-java/releases/download/v${PYROSCOPE_AGENT_VERSION}/pyroscope.jar /pyroscope/pyroscope.jar
COPY --from=build /src/build/libs/zc.jar /app/zc.jar
# 에이전트는 이미지에 넣어 두기만 한다. 켤지 말지는 compose 의 JAVA_TOOL_OPTIONS 가 정한다.
ENTRYPOINT ["java", "-jar", "/app/zc.jar"]
