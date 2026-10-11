FROM python:3.13-slim
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends fonts-nanum >/dev/null && rm -rf /var/lib/apt/lists/* \
 && pip install -q --no-cache-dir matplotlib==3.11.2
WORKDIR /work
ENTRYPOINT ["python", "-u"]
