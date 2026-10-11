FROM gradle:9-jdk21 AS build
WORKDIR /src
COPY settings.gradle build.gradle ./
COPY src ./src
RUN gradle bootJar --no-daemon -q

FROM eclipse-temurin:21-jre
COPY --from=build /src/build/libs/resil.jar /app/resil.jar
ENTRYPOINT ["java", "-jar", "/app/resil.jar"]
