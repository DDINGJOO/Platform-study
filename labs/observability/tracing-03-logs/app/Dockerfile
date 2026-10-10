FROM gradle:9-jdk21 AS build
WORKDIR /src
COPY settings.gradle build.gradle ./
COPY src ./src
RUN gradle bootJar --no-daemon -q

FROM eclipse-temurin:21-jre
ARG OTEL_AGENT_VERSION=2.32.0
ADD https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/download/v${OTEL_AGENT_VERSION}/opentelemetry-javaagent.jar /otel/opentelemetry-javaagent.jar
COPY --from=build /src/build/libs/shop.jar /app/shop.jar
# 에이전트는 이미지에 넣어 두기만 한다. 켤지 말지는 compose 의 JAVA_TOOL_OPTIONS 가 정한다.
ENTRYPOINT ["java", "-jar", "/app/shop.jar"]
