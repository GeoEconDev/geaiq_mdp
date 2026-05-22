FROM python:3.11-slim

# Create a working directory
WORKDIR /app

# Install base dependencies
RUN apt-get update
RUN apt-get -y install git
RUN pip install --upgrade pip
COPY requirements.txt /app/
RUN pip install -r requirements.txt

# Copy source code
COPY . /app/

# Install source
RUN pip install --no-cache-dir .

# Create the data directory
RUN mkdir -p /tmp/geoecon_metadata/data \
            /tmp/geoecon_metadata/menu \
            /tmp/geoecon_metadata/metadata

# Set the entrypoint (adjust as needed)
ENTRYPOINT ["gemd", "--context", "docker", "--root", "/tmp/geoecon_metadata", "--target", "dev"]
# docker run --rm -e GIT_COMMIT=df5f2efe -e GIT_TOKEN={TOKEN} -it metadata:latest check \
#   --format html --output arg_2019_concentracion_electoral_adm2.html \
#   metadata\argentina\arg_2019_concentracion_electoral_adm2.yml