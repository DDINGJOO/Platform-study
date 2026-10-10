# syntax=docker/dockerfile:1
FROM gradle:9-jdk21 AS build
WORKDIR /src
COPY settings.gradle build.gradle ./
COPY src ./src
RUN --mount=type=cache,target=/home/gradle/.gradle gradle bootJar --no-daemon -q

FROM eclipse-temurin:21-jre
COPY --from=build /src/build/libs/*.jar /app/app.jar
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
