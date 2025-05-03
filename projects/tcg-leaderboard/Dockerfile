FROM python:3.13-slim-bookworm
WORKDIR /opt/cloud-bot
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py ./
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh
EXPOSE 8000
CMD ["./entrypoint.sh"]