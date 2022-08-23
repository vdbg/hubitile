# Alpine for smaller size
FROM python:3.9-alpine

# Create a system account hubitile.hubitile
RUN addgroup -S hubitile && adduser -S hubitile -G hubitile
# Non-alpine equivalent of above:
#RUN groupadd -r hubitile && useradd -r -m -g hubitile hubitile

USER hubitile

WORKDIR /app

# set environment variables
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing pyc files to disc
# PYTHONUNBUFFERED: Prevents Python from buffering stdout and stderr
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements.txt     /app

RUN pip install --no-cache-dir --upgrade pip --no-warn-script-location && \
    pip install --no-cache-dir -r ./requirements.txt --no-warn-script-location 

COPY *.py                 /app/
COPY template.config.yaml /app/

ENTRYPOINT python main.py
