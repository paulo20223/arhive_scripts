import os
from typing import List
from django import setup
from django.contrib import messages

setup()
import nginx
from core.settings import BASE_UPSTREAM, BASE_DIR

class NginxConfig:
    def __init__(self, servers):
        self.config = nginx.Conf()
        self.servers = servers # [{"domain": "example.com", "is_certificate": True}]

    @classmethod
    def generate(cls, servers):
        obj = cls(servers)
        obj.upstream()
        obj.base_server()
        obj.servers(80)
        obj.servers(443)
        obj.certificate()
        # Здесь указать папку куда выгружать конфиг
        nginx.dumpf(obj.config, f'{BASE_DIR}/etc/nginx.conf')
        obj.success_message("Настройки сервера обновленны")
        os.system('nginx -s reload')

    def upstream(self):
        for upstream_name, upstream_url in BASE_UPSTREAM.items():
            upstream_obj = nginx.Upstream(upstream_name, nginx.Key("server", upstream_url))
            self.config.add(upstream_obj)

    def certificate(self, servers):
        for server_data in servers:
            if server_data.get("is_ssl_certificate", False):
                domain = server_data.get("domain", "")
                conf = nginx.Conf()
                conf.add(nginx.Key("ssl_certificate", f"/var/www/certificate/{domain}-cert.pem"))
                conf.add(nginx.Key("ssl_certificate_key", f"/var/www/certificate/{domain}-key.pem"))
                nginx.dumpf(conf, f'/etc/nginx/conf.d/ssl_certificate/{domain}.conf')

    def base_server(self):
        server = nginx.Server()
        server.add(
            nginx.Key('server_name', '0.0.0.0'),

            nginx.Location('/',
                           nginx.Key("try_files", "$uri @proxy_to_app")),
            nginx.Location('@proxy_to_app',
                           nginx.Key('proxy_set_header', "X-Forwarded-For $proxy_add_x_forwarded_for"),
                           nginx.Key('proxy_set_header', "X-Forwarded-Proto $scheme"),
                           nginx.Key('proxy_set_header', "Host $http_host"),
                           nginx.Key('proxy_redirect', "off"),
                           nginx.Key('add_header', "Last-Modified $date_gmt"),
                           nginx.Key('add_header', "Cache-Control 'no-store, no-cache, must-revalidate, "
                                                   "proxy-revalidate, max-age=0'"),
                           nginx.Key('if_modified_since', "off"),
                           nginx.Key('expires', "off"),
                           nginx.Key('etag', "off"),
                           nginx.Key('proxy_no_cache', "1"),
                           nginx.Key('proxy_cache_bypass', "1"),
                           nginx.Key('proxy_pass', f"http://base_server"),
                           ),
            nginx.Location("/static/",
                           nginx.Key('autoindex', 'on'),
                           nginx.Key('alias', '/var/www/static/'),
                           nginx.Key('add_header', 'Cache-Control no-cache')),
            nginx.Location("/media/",
                           nginx.Key('autoindex', 'on'),
                           nginx.Key('alias', '/var/www/media/'),
                           nginx.Key('add_header', 'Cache-Control no-cache')),
        )
        server.add(nginx.Key("listen", '8018'))
        server.add(nginx.Key("listen", '[::]:8018'))

        self.config.add(
            server
        )

    def servers(self, port):
        for server_data in self.servers:
            server = nginx.Server()
            domain = server_data.get("domain", "")
            if port == 80 and server_data.get("is_ssl_certificate", False):

                server.add(nginx.Key('server_name', domain),
                           nginx.Key('return', "301 https://$host$request_uri"), )
                server.add(nginx.Key("listen", f'{port}'))
                server.add(nginx.Key("listen", f'[::]:{port}'))
            else:
                if server_data.get("is_ssl_certificate", False):
                    server.add(
                        nginx.Key('include', f'/etc/nginx/conf.d/ssl_certificate/{domain}.*'),
                    )
                server.add(
                    nginx.Key('server_name', domain),

                    nginx.Location('/',
                                   nginx.Key("try_files", "$uri @proxy_to_app")),
                    nginx.Location('@proxy_to_app',
                                   nginx.Key('rewrite', f"^ /{domain}$request_uri break"),
                                   nginx.Key('proxy_set_header', "X-Forwarded-For $proxy_add_x_forwarded_for"),
                                   nginx.Key('proxy_set_header', "X-Forwarded-Proto $scheme"),
                                   nginx.Key('proxy_set_header', "Host $http_host"),
                                   nginx.Key('add_header', "Last-Modified $date_gmt"),
                                   nginx.Key('add_header',
                                             "Cache-Control 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0'"),
                                   nginx.Key('if_modified_since', "off"),
                                   nginx.Key('expires', "off"),
                                   nginx.Key('etag', "off"),
                                   nginx.Key('proxy_no_cache', "1"),
                                   nginx.Key('proxy_cache_bypass', "1"),
                                   nginx.Key('proxy_redirect', "off"),
                                   nginx.Key('proxy_pass', f"http://base_server"),
                                   ),
                    nginx.Location("/static/",
                                   nginx.Key('autoindex', 'on'),
                                   nginx.Key('alias', '/var/www/static/'),
                                   nginx.Key('add_header', 'Cache-Control no-cache')),
                    nginx.Location("/media/",
                                   nginx.Key('autoindex', 'on'),
                                   nginx.Key('alias', '/var/www/media/'),
                                   nginx.Key('add_header', 'Cache-Control no-cache')),
                )
                server.add(nginx.Key("listen", f'{port} ssl'))
                server.add(nginx.Key("listen", f'[::]:{port}'))

            self.config.add(
                server
            )


if __name__ == '__main__':
    NginxConfig.generate()
