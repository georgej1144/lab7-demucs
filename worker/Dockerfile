# use the demucs image as a base
FROM xserrat/facebook-demucs:latest

# live somewhere
WORKDIR /var/app

# install all our deps
RUN pip install --no-cache-dir redis requests minio
# put script in /var/app/worker-server.py
COPY worker-server.py .
# run it
CMD ["python3", "worker-server.py"]