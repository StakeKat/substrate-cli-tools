###########################################
# Dirty build image just creates wheels
###########################################
FROM python:3.9-slim-bullseye as buildimg

COPY requirements.txt /requirements.txt

# Main additional stuff
RUN apt-get update
RUN apt-get -y install ruby ruby-dev
RUN apt-get -y install rustc
RUN apt-get -y install git

# Upgrade pip
RUN pip install --upgrade pip setuptools wheel
RUN pip install -U pre-commit
RUN gem install rubocop --no-doc

# Create wheels
RUN pip wheel --wheel-dir=/local/wheels -r requirements.txt

###########################################
# Actual final image using just wheels
###########################################
FROM python:3.9-slim-bullseye

# Copy all
COPY subtools /subtools
COPY subclient /subclient
COPY abis /abis
COPY requirements.txt /requirements.txt
COPY --from=buildimg /local/wheels /local/wheels

# Install requirements from wheels
RUN pip install \
      --no-index \
      --find-links=/local/wheels \
      -r requirements.txt

# Main entry point
CMD [ "/bin/sh" ]