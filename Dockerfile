FROM python:3.10.0-slim

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python3 manage.py migrate
RUN python3 manage.py collectstatic

EXPOSE 8000

CMD [ "waitress-serve", "--listen=0.0.0.0:8000", "project.wsgi:application" ]
