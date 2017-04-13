FROM python:2.7

RUN mkdir /root/SteamyReviews

WORKDIR /root/SteamyReviews

# Install the required modules
ADD requirements.txt .
RUN pip install -r requirements.txt
