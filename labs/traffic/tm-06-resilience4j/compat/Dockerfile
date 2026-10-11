FROM gradle:9-jdk21 AS build
ARG MODULE=spring-boot4
WORKDIR /src
COPY settings.gradle build.gradle ./
COPY src ./src
RUN gradle bootJar --no-daemon -q -Pmodule=${MODULE}

FROM eclipse-temurin:21-jre
COPY --from=build /src/build/libs/compat.jar /app/compat.jar
ENTRYPOINT ["java", "-jar", "/app/compat.jar"]
