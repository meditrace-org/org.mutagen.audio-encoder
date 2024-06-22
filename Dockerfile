FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime


ENV RABBITMQ__PREFETCH_COUNT=3

#set up environment
RUN apt-get update \
    && apt-get install -y python3 wget gnupg2 software-properties-common\
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-ubuntu2004.pin
RUN  mv cuda-ubuntu2004.pin /etc/apt/preferences.d/cuda-repository-pin-600
RUN  apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/3bf863cc.pub \
     && add-apt-repository "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/ /" \
     && apt-get update \
     && apt-get install libcudnn8 \
     && apt-get install libcudnn8-dev

WORKDIR /home

COPY ./requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

COPY / .

CMD ["python3", "-m", "app"]