FROM postgis/postgis:16-3.5-alpine

# Install build dependencies and git
RUN apk add --no-cache --virtual .build-deps \
    git \
    make \
    gcc \
    musl-dev \
    postgresql16-dev \
    && apk add --no-cache postgresql16-contrib

# Clone and install pgjwt
RUN git clone https://github.com/michelp/pgjwt.git /tmp/pgjwt \
    && cd /tmp/pgjwt \
    && make install \
    && rm -rf /tmp/pgjwt

# Clean up build dependencies
RUN apk del .build-deps

# Add your SECRET_KEY to PostgreSQL configuration
RUN echo "shared_preload_libraries = ''" >> /usr/local/share/postgresql/postgresql.conf.sample