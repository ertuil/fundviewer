FROM python:3.11

RUN pip install akshare beautifulsoup4 requests django uvicorn mysqlclient redis

WORKDIR /app

CMD ["uvicorn", "fundviewer.asgi:application", "--reload"]