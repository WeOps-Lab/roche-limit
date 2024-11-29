FROM ubuntu:22.04

RUN apt-get update && \
    apt-get install -y libhdf5-dev vim python3 python3-pip unzip curl pkg-config libssl-dev libffi-dev supervisor libgl1-mesa-glx && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

ADD . .

ADD support-files/supervisor/service.conf /etc/supervisor/conf.d/service.conf
RUN pip install -r ./requirements/requirements.txt
RUN pip install -r ./requirements/requirements-extra.txt
ADD https://paddleocr.bj.bcebos.com/ppstructure/models/slanet/ch_ppstructure_mobile_v2.0_SLANet_infer.tar /root/.paddleocr/whl/table/ch_ppstructure_mobile_v2.0_SLANet_infer/ch_ppstructure_mobile_v2.0_SLANet_infer.tar
ADD https://paddleocr.bj.bcebos.com/ppstructure/models/layout/picodet_lcnet_x1_0_fgd_layout_cdla_infer.tar /root/.paddleocr/whl/layout/picodet_lcnet_x1_0_fgd_layout_cdla_infer/picodet_lcnet_x1_0_fgd_layout_cdla_infer.tar

CMD ["supervisord", "-n"]