# 태그 재푸시 실험용 이미지. CONTENT 만 바꿔 두 번 빌드한다.
FROM busybox:1.37.0
ARG CONTENT=v1
RUN echo "$CONTENT" > /content.txt
CMD ["sh", "-c", "cat /content.txt; sleep 3600"]
