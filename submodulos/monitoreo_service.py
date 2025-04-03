"""
Servicio de monitoreo para integrar Prometheus y Grafana
"""
import logging
import threading
from .exportador_proxmox import exportador_proxmox
from .prometheus_service import servicio_prometheus
from .grafana_service import servicio_grafana

logger = logging.getLogger(__name__)

class ServicioMonitoreo:
    """
    Servicio principal para coordinar el monitoreo de Proxmox con Prometheus y Grafana
    """
    
    def __init__(self):
        """Inicializa el servicio de monitoreo"""
        self.exportador = exportador_proxmox
        self.prometheus = servicio_prometheus
        self.grafana = servicio_grafana
        self.hilo_exportador = None
        self.activo = False
    
    def iniciar_todo(self):
        """
        Inicia todos los componentes del sistema de monitoreo
        
        Returns:
            dict: Estado de cada componente después del inicio
        """
        resultados = {
            'prometheus': False,
            'grafana': False,
            'exportador': False
        }
        
        # 1. Primero iniciar Prometheus
        logger.info("Iniciando Prometheus...")
        resultados['prometheus'] = self.prometheus.iniciar()
        
        # 2. Iniciar Grafana después de Prometheus
        if resultados['prometheus']:
            logger.info("Iniciando Grafana...")
            resultados['grafana'] = self.grafana.iniciar()
        else:
            logger.error("No se pudo iniciar Grafana porque Prometheus no se inició correctamente")
        
        # 3. Iniciar el exportador de Proxmox en un hilo separado
        if not self.hilo_exportador or not self.hilo_exportador.is_alive():
            logger.info("Iniciando exportador de Proxmox...")
            self.hilo_exportador = threading.Thread(
                target=self.exportador.iniciar,
                daemon=True  # El hilo se cerrará si el programa principal termina
            )
            self.hilo_exportador.start()
            resultados['exportador'] = True
        else:
            logger.info("El exportador de Proxmox ya está en ejecución")
            resultados['exportador'] = True
        
        self.activo = all(resultados.values())
        
        return resultados
    
    def detener_todo(self):
        """
        Detiene todos los componentes del sistema de monitoreo
        
        Returns:
            dict: Estado de cada componente después de la detención
        """
        resultados = {
            'prometheus': True,  # Asumimos éxito si ya estaba detenido
            'grafana': True,
            'exportador': True
        }
        
        # No podemos detener el hilo del exportador directamente, pero podemos
        # marcar el servicio como inactivo
        self.activo = False
        
        # Detener Grafana
        if self.grafana.verificar_estado():
            logger.info("Deteniendo Grafana...")
            resultados['grafana'] = self.grafana.detener()
        
        # Detener Prometheus
        if self.prometheus.verificar_estado():
            logger.info("Deteniendo Prometheus...")
            resultados['prometheus'] = self.prometheus.detener()
        
        return resultados
    
    def reiniciar_todo(self):
        """
        Reinicia todos los componentes del sistema de monitoreo
        
        Returns:
            dict: Estado de cada componente después del reinicio
        """
        self.detener_todo()
        return self.iniciar_todo()
    
    def verificar_estado(self):
        """
        Verifica el estado de todos los componentes
        
        Returns:
            dict: Estado actual de cada componente
        """
        return {
            'prometheus': self.prometheus.verificar_estado(),
            'grafana': self.grafana.verificar_estado(),
            'exportador': self.hilo_exportador is not None and self.hilo_exportador.is_alive(),
            'activo': self.activo
        }
    
    def obtener_urls(self):
        """
        Devuelve las URLs de acceso a Prometheus y Grafana
        
        Returns:
            dict: URLs de los servicios
        """
        return {
            'prometheus': 'http://localhost:9090',
            'grafana': 'http://localhost:3000'
        }

# Instancia singleton para usar en toda la aplicación
servicio_monitoreo = ServicioMonitoreo()