# Static demo site for Cloud Run: nginx listening on $PORT (Cloud Run injects PORT=8080)
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY site/ /usr/share/nginx/html/
ENV PORT=8080
EXPOSE 8080
