# HaMivtzar News Lab — intentionally vulnerable practice target.
# Build:  docker build -t hamivtzar-lab .
# Run:    docker run --rm -p 127.0.0.1:8099:8099 hamivtzar-lab
#
# NOTE: bind to 127.0.0.1 only. Do NOT publish this container to a public
# network — it is deliberately insecure.
FROM python:3.12-slim

WORKDIR /app
COPY . /app

# Zero third-party deps: standard library only.
ENV HOST=0.0.0.0 PORT=8099
EXPOSE 8099

# Drop root inside the container as a small hardening nicety (the *app* is
# intentionally vulnerable; the container needn't be).
RUN useradd -m lab
USER lab

CMD ["python3", "app.py"]
