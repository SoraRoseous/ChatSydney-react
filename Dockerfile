FROM python:3.11

WORKDIR ./ChatSydney

ADD . .

RUN pip install -r requirements.txt --upgrade

EXPOSE 65432

CMD ["python", "./main.py"]
