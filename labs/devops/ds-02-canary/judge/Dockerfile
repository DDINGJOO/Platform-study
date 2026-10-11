FROM python:3.13-alpine
COPY mannwhitney.py judge.py /judge/
USER 65534
CMD ["python", "-u", "/judge/judge.py"]
