FROM arm32v7/python:3.11-slim-bookworm
WORKDIR /app
COPY ./requirements.txt /app

# For numpy
RUN apt-get update && apt-get install libgfortran5 libopenblas0-pthread 
# Install packages form piwheel index: pre-compiled binary Python packages for ARM
RUN pip install --index-url=https://www.piwheels.org/simple --no-cache-dir -r requirements.txt 
RUN apt-get install libxslt1.1 -y && pip install --index-url=https://www.piwheels.org/simple --no-cache-dir lxml && pip install --no-cache-dir BeautifulSoup4

ENTRYPOINT ["python", "measure.py"]
