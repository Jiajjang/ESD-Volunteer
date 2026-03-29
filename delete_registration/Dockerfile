FROM python:3-slim
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY delete_reg.py ./
CMD [ "python", "./delete_reg.py" ]