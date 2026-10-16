FROM nginx:1.29-alpine
# 절차서를 실행할 도구: bash, psql, flock(util-linux), curl
RUN apk add --no-cache bash postgresql-client flock curl procps
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY entry.sh /entry.sh
RUN mkdir -p /etc/nginx/apps && echo 'location /t/base/ { proxy_pass http://app:8080/; }' > /etc/nginx/apps/apps.conf
# nginx 를 PID 1 로 두지 않는다. 스크립트가 nginx 를 멈췄다 켜도 컨테이너는 살아 있어야 한다
ENTRYPOINT ["/entry.sh"]
