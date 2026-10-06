"""
ASGI config for smartworker project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

import django_service_urls.loads  # interpreta as URLs de serviço do settings

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartworker.settings')

application = get_asgi_application()
