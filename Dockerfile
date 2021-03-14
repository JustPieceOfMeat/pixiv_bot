FROM python:slim

ENV DOCKER=TRUE

RUN mkdir /app
WORKDIR /app

ADD requirements_docker.txt .
RUN pip install -r requirements_docker.txt

ADD . .

CMD ["python", "main.py"]