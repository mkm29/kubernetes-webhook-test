FROM python:3.10-alpine3.16 AS parent
WORKDIR /app
RUN pip3 install pipenv
COPY Pipfile /app/
COPY Pipfile.lock /app/


FROM parent AS base
RUN pipenv install --deploy --system


FROM parent AS dev-base
RUN pipenv install --deploy --system --dev


FROM dev-base AS CLI
RUN apk add --no-cache --update openssl
COPY tasks.py /app/
ENTRYPOINT ["invoke", "keys"]


FROM dev-base AS Test
COPY src /app
RUN pipenv check --system
RUN pytest


FROM base as Prod
COPY src /app
EXPOSE 8080
ENTRYPOINT [ "gunicorn" ]
CMD ["--bind", "0.0.0.0:8080", "app:app"]