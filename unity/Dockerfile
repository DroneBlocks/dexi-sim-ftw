FROM nginx:alpine

# Copy nginx config first
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy all files to nginx html directory
COPY . /usr/share/nginx/html

EXPOSE 1337

CMD ["nginx", "-g", "daemon off;"]
