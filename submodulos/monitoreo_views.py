"""
Vistas para la funcionalidad de monitoreo
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .monitoreo_service import servicio_monitoreo

@login_required
def panel_monitoreo(request):
    """
    Vista principal del panel de monitoreo
    """
    # Obtener estado actual de los servicios
    estado = servicio_monitoreo.verificar_estado()
    urls = servicio_monitoreo.obtener_urls()
    
    return render(request, 'monitoreo/panel.html', {
        'estado': estado,
        'urls': urls
    })

@login_required
def iniciar_servicios(request):
    """
    Inicia todos los servicios de monitoreo
    """
    resultados = servicio_monitoreo.iniciar_todo()
    
    if all(resultados.values()):
        messages.success(request, "Todos los servicios de monitoreo se han iniciado correctamente")
    else:
        servicios_fallidos = [s for s, v in resultados.items() if not v]
        messages.error(request, f"No se pudieron iniciar algunos servicios: {', '.join(servicios_fallidos)}")
    
    # Si es una petición AJAX, devolver JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': all(resultados.values()),
            'resultados': resultados
        })
    
    return redirect('panel_monitoreo')

@login_required
def detener_servicios(request):
    """
    Detiene todos los servicios de monitoreo
    """
    resultados = servicio_monitoreo.detener_todo()
    
    if all(resultados.values()):
        messages.success(request, "Todos los servicios de monitoreo se han detenido correctamente")
    else:
        servicios_fallidos = [s for s, v in resultados.items() if not v]
        messages.error(request, f"No se pudieron detener algunos servicios: {', '.join(servicios_fallidos)}")
    
    # Si es una petición AJAX, devolver JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': all(resultados.values()),
            'resultados': resultados
        })
    
    return redirect('panel_monitoreo')

@login_required
def reiniciar_servicios(request):
    """
    Reinicia todos los servicios de monitoreo
    """
    resultados = servicio_monitoreo.reiniciar_todo()
    
    if all(resultados.values()):
        messages.success(request, "Todos los servicios de monitoreo se han reiniciado correctamente")
    else:
        servicios_fallidos = [s for s, v in resultados.items() if not v]
        messages.error(request, f"No se pudieron reiniciar algunos servicios: {', '.join(servicios_fallidos)}")
    
    # Si es una petición AJAX, devolver JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': all(resultados.values()),
            'resultados': resultados
        })
    
    return redirect('panel_monitoreo')

@login_required
def estado_servicios(request):
    """
    Devuelve el estado actual de los servicios de monitoreo
    """
    estado = servicio_monitoreo.verificar_estado()
    
    return JsonResponse({
        'success': True,
        'estado': estado
    })

@login_required
def iframe_grafana(request, dashboard=None):
    """
    Vista para mostrar un dashboard de Grafana en un iframe
    """
    urls = servicio_monitoreo.obtener_urls()
    grafana_url = urls['grafana']
    
    if dashboard:
        grafana_url += f"/d/{dashboard}"
    
    return render(request, 'monitoreo/iframe_grafana.html', {
        'grafana_url': grafana_url
    })

@login_required
def iframe_prometheus(request):
    """
    Vista para mostrar la interfaz de Prometheus en un iframe
    """
    urls = servicio_monitoreo.obtener_urls()
    prometheus_url = urls['prometheus']
    
    return render(request, 'monitoreo/iframe_prometheus.html', {
        'prometheus_url': prometheus_url
    })