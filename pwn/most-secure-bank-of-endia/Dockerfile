FROM python:3.12-slim
WORKDIR /opt/boe

COPY bin/ledgerd /opt/boe/bin/ledgerd
COPY app/ /opt/boe/app/

RUN pip install --no-cache-dir -r app/requirements.txt
RUN echo 'kBxAc{TEST_FLAG}' > /flag.txt

ENV LEDGERD_PATH=/opt/boe/bin/ledgerd
EXPOSE 5000

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "--chdir", "/opt/boe/app", "app:app"]
