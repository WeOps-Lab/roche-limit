FROM ubuntu:22.04

RUN apt-get update && \
    apt-get install -y libhdf5-dev vim python3 python3-pip unzip curl pkg-config libssl-dev libffi-dev supervisor && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

ADD . .

ADD support-files/supervisor/service.conf /etc/supervisor/conf.d/service.conf

RUN pip install pip-tools
RUN pip-compile ./requirements/requirements.txt ./requirements/requirements-extra.txt -v --output-file ./requirements.txt
RUN pip install -r requirements.txt

CMD ["supervisord", "-n"]