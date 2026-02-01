FROM caddy:alpine

RUN apk add --no-cache avahi avahi-tools dbus

COPY avahi-daemon.conf /etc/avahi/avahi-daemon.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
