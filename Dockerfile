FROM python:3.10.0-alpine

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
ARG domain=p2triage
ARG config=config.ini.template
ENV CONFIG_GROUP=DEFAULT
ENV TA3_PORT=8080
ENV TEST=
COPY requirements.txt /usr/src/app/
# Uncomment if your environment requires that pip specify a local certificate
#COPY ca-bundle.crt ./
#ENV PIP_CERT=ca-bundle.crt

RUN pip3 install --no-cache-dir -r requirements.txt

COPY . /usr/src/app
COPY swagger_server/itm/data/domains/$domain/$config /usr/src/app/swagger_server/config.ini
EXPOSE $TA3_PORT

# Print the environment variables
RUN echo "Config group: $CONFIG_GROUP"
RUN echo "Config file: $domain/$config"
RUN echo "Domain: $domain"
RUN echo "Port: $TA3_PORT"

CMD ["sh", "-c", "python3 -m swagger_server -c $CONFIG_GROUP $TEST"]
