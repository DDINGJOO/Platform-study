FROM python:3.13-slim
RUN pip install --no-cache-dir numpy==2.3.3 scipy==1.16.2 matplotlib==3.10.6
WORKDIR /results
ENTRYPOINT ["python", "/fit/fit.py"]
COPY fit.py plot_cpu.py sim_degeneracy.py /fit/
