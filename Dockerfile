FROM python:3.11

RUN pip install akshare beautifulsoup4 requests django uvicorn

WORKDIR /app

CMD ["uvicorn", "fundviewer.asgi:application", "--reload"]