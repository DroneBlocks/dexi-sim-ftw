FROM nginx:alpine

# Copy nginx config first
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy HTML files
COPY index.html /usr/share/nginx/html/

# Copy TemplateData directory (CSS, images, etc.)
COPY TemplateData /usr/share/nginx/html/TemplateData

# Copy Unity build files (will use .br files if available, otherwise uncompressed)
COPY Build /usr/share/nginx/html/Build

# Fix permissions on build files (Unity exports .br files with 600 permissions)
RUN chmod -R 644 /usr/share/nginx/html/Build/* && \
    chmod 755 /usr/share/nginx/html/Build

EXPOSE 1337

CMD ["nginx", "-g", "daemon off;"]
