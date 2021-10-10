FROM python:3.8-slim

RUN mkdir -p /karsa-backend

WORKDIR /karsa-backend
COPY ./src/external-requirements.txt .
RUN pip install --no-cache-dir -r external-requirements.txt

COPY . .

WORKDIR /karsa-backend/src

RUN pip install --no-cache-dir -r internal-requirements.txt

WORKDIR /karsa-backend
ENTRYPOINT [ "./entrypoint.sh" ]