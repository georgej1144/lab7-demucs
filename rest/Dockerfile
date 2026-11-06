# use same version we dev'd with (but slim)
FROM python:3.12-slim

# live somewhere
WORKDIR /var/app
# open port
EXPOSE 5000

# install all our deps
RUN pip install --no-cache-dir redis requests flask minio
# put script in /var/app/rest-server.py
COPY rest-server.py .
# run it
CMD ["python3", "rest-server.py"]