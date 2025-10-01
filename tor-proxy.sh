docker run -d \
  --name tor-proxy \
  -p 8118:8118 \
  -p 9050:9050 \
  dperson/torproxy