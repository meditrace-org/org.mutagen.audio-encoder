FROM pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime

#set up environment
RUN apt-get update \
    && apt-get install -y python3 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /home

COPY ./requirfixements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

COPY / .

CMD ["python3", "-m", "app"]