FROM python:3.8

WORKDIR ./ChatSydney

ADD . .

RUN pip install -r requirements.txt

EXPOSE 65432

CMD ["python", "./main.py"]
