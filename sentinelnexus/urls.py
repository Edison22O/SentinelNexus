"""sentinelnexus URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from . import views
from submodulos import monitoreo_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('nodes/<str:node_name>/', views.node_detail, name='node_detail'),
    path('vms/<str:node_name>/<int:vmid>/', views.vm_detail, name='vm_detail'),
    path('vms/<str:node_name>/<int:vmid>/<str:vm_type>/', views.vm_detail, name='vm_detail_with_type'),
    path('vms/<str:node_name>/<int:vmid>/<str:action>/', views.vm_action, name='vm_action'),
    path('vms/<str:node_name>/<int:vmid>/<str:vm_type>/<str:action>/', views.vm_action, name='vm_action_with_type'),
    
    # API endpoints
    path('api/nodes/', views.api_get_nodes, name='api_nodes'),
    path('api/vms/', views.api_get_vms, name='api_vms'),
    path('api/vms/<str:node_name>/<int:vmid>/status/', views.api_vm_status, name='api_vm_status'),

    # Rutas de monitoreo
    path('monitoreo/', monitoreo_views.panel_monitoreo, name='panel_monitoreo'),
    path('monitoreo/iniciar/', monitoreo_views.iniciar_servicios, name='iniciar_servicios'),
    path('monitoreo/detener/', monitoreo_views.detener_servicios, name='detener_servicios'),
    path('monitoreo/reiniciar/', monitoreo_views.reiniciar_servicios, name='reiniciar_servicios'),
    path('monitoreo/estado/', monitoreo_views.estado_servicios, name='estado_servicios'),
    path('monitoreo/grafana/', monitoreo_views.iframe_grafana, name='iframe_grafana'),
    path('monitoreo/grafana/<str:dashboard>/', monitoreo_views.iframe_grafana, name='iframe_grafana'),
    path('monitoreo/prometheus/', monitoreo_views.iframe_prometheus, name='iframe_prometheus'),
]