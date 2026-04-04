FROM nginx:alpine

# Copy nginx config
COPY avr-2025-sim/nginx.conf /etc/nginx/conf.d/default.conf

# Copy HTML files
COPY avr-2025-sim/index.html /usr/share/nginx/html/

# Copy Unity build files
COPY avr-2025-sim/Build /usr/share/nginx/html/Build

# Fix permissions on build files
RUN chmod -R 644 /usr/share/nginx/html/Build/* && \
    chmod 755 /usr/share/nginx/html/Build

EXPOSE 1337

CMD ["nginx", "-g", "daemon off;"]
