FROM python:3.10.0-alpine

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
ARG domain=p2triage
ENV CONFIG_GROUP=DEFAULT
ENV TA3_PORT=8080
ENV TEST=
COPY requirements.txt /usr/src/app/

RUN pip3 install --no-cache-dir -r requirements.txt

COPY . /usr/src/app
COPY swagger_server/itm/data/domains/$domain/config.ini.template /usr/src/app/swagger_server/config.ini
EXPOSE $TA3_PORT

# Print the environment variables
RUN echo "Config group: $CONFIG_GROUP"
RUN echo "Domain: $domain"
RUN echo "Port: $TA3_PORT"

CMD ["sh", "-c", "python3 -m swagger_server -c $CONFIG_GROUP $TEST"]
