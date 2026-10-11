# 빌드 도구 없이 메이븐 센트럴에서 jar 를 받아 javac 로 컴파일한다.
FROM eclipse-temurin:21-jdk AS build
ARG DROPWIZARD=4.2.40
ARG MICROMETER=1.17.1
WORKDIR /lib
RUN set -e; M=https://repo1.maven.org/maven2; \
    curl -fsSLO $M/io/dropwizard/metrics/metrics-core/$DROPWIZARD/metrics-core-$DROPWIZARD.jar; \
    curl -fsSLO $M/org/slf4j/slf4j-api/2.0.17/slf4j-api-2.0.17.jar; \
    curl -fsSLO $M/io/micrometer/micrometer-core/$MICROMETER/micrometer-core-$MICROMETER.jar; \
    curl -fsSLO $M/io/micrometer/micrometer-commons/$MICROMETER/micrometer-commons-$MICROMETER.jar; \
    curl -fsSLO $M/io/micrometer/micrometer-observation/$MICROMETER/micrometer-observation-$MICROMETER.jar; \
    curl -fsSLO $M/org/hdrhistogram/HdrHistogram/2.2.2/HdrHistogram-2.2.2.jar; \
    curl -fsSLO $M/org/jspecify/jspecify/1.0.0/jspecify-1.0.0.jar
WORKDIR /src
COPY EwmaLab.java .
RUN javac -cp '/lib/*' -d /out EwmaLab.java

FROM eclipse-temurin:21-jre
COPY --from=build /lib /lib
COPY --from=build /out /app
ENTRYPOINT ["java", "-cp", "/app:/lib/*", "EwmaLab"]
