FROM python:2.7

RUN mkdir /root/SteamyReviews
WORKDIR /root/SteamyReviews

ADD requirements.txt .
RUN pip install -r requirements.txt
RUN python -c "import nltk; nltk.download('punkt')"

ADD data data/
ADD mallet mallet/
ADD app app/
ADD *.py ./

CMD gunicorn -w 4 app:app
