FROM gradle:9-jdk21 AS build
WORKDIR /src
COPY settings.gradle build.gradle ./
COPY src ./src
RUN gradle bootJar --no-daemon -q

FROM eclipse-temurin:21-jre
COPY --from=build /src/build/libs/slo-app.jar /app/slo-app.jar
ENTRYPOINT ["java", "-jar", "/app/slo-app.jar"]
