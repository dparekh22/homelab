FROM python:3.13-slim-bookworm
WORKDIR /opt/cloud-bot
COPY python/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install alembic
COPY python/*.py ./
COPY docker/entrypoint.sh .  
RUN chmod +x entrypoint.sh
EXPOSE 8000
CMD ["./entrypoint.sh"]