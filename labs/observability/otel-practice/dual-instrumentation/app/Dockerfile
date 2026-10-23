FROM gradle:9.8.1-jdk21 AS build
WORKDIR /src
COPY settings.gradle build.gradle ./
COPY src ./src
RUN --mount=type=cache,target=/home/gradle/.gradle gradle bootJar --no-daemon -q -Dorg.gradle.jvmargs=-Xmx256m
FROM eclipse-temurin:21-jre
ARG OTEL_AGENT_VERSION=2.32.0
ADD https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/download/v${OTEL_AGENT_VERSION}/opentelemetry-javaagent.jar /otel/agent.jar
COPY --from=build /src/build/libs/dual-instrumentation.jar /app/app.jar
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
