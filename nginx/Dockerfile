FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY locations.conf /etc/nginx/conf.d/locations.conf
EXPOSE 80 443
CMD ["nginx", "-g", "daemon off;"]
