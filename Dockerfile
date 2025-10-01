FROM python:3.11.2-slim-buster
# FROM python:3.10-buster
# FROM python:3.11-buster

WORKDIR /app

COPY ./requirements.txt .
# COPY ./.env . 
RUN pip install -r requirements.txt 

RUN pip install watchfiles 


EXPOSE 8000

COPY . .

RUN chmod -R 777 /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]