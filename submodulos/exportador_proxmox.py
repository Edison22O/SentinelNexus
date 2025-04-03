"""
Exportador de métricas de Proxmox para Prometheus
"""
from prometheus_client import start_http_server, Gauge, Counter
import time
from django.conf import settings
from .proxmox_service import proxmox_service
import logging

logger = logging.getLogger(__name__)

class ExportadorProxmox:
    """
    Exportador de métricas de Proxmox VE para Prometheus
    """
    
    def __init__(self, puerto=9090, intervalo_segundos=30):
        """
        Inicializa el exportador con la configuración proporcionada
        
        Args:
            puerto (int): El puerto para exponer las métricas
            intervalo_segundos (int): Con qué frecuencia consultar Proxmox para obtener nuevas métricas
        """
        self.puerto = puerto
        self.intervalo_segundos = intervalo_segundos
        self.proxmox_service = proxmox_service
        
        # Métricas de nodos
        self.nodo_activo = Gauge('proxmox_nodo_activo', 'Estado del nodo (1 = activo, 0 = inactivo)', ['nodo'])
        self.nodo_uso_cpu = Gauge('proxmox_nodo_uso_cpu_ratio', 'Ratio de uso de CPU del nodo', ['nodo'])
        self.nodo_memoria_total = Gauge('proxmox_nodo_memoria_total_bytes', 'Memoria total del nodo en bytes', ['nodo'])
        self.nodo_memoria_usada = Gauge('proxmox_nodo_memoria_usada_bytes', 'Memoria usada del nodo en bytes', ['nodo'])
        self.nodo_memoria_libre = Gauge('proxmox_nodo_memoria_libre_bytes', 'Memoria libre del nodo en bytes', ['nodo'])
        self.nodo_uptime = Gauge('proxmox_nodo_uptime_segundos', 'Tiempo de actividad del nodo en segundos', ['nodo'])
        
        # Métricas de VM
        self.vm_activa = Gauge('proxmox_vm_activa', 'Estado de la VM (1 = ejecutando, 0 = detenida)', ['nodo', 'vmid', 'nombre', 'tipo'])
        self.vm_uso_cpu = Gauge('proxmox_vm_uso_cpu_ratio', 'Ratio de uso de CPU de la VM', ['nodo', 'vmid', 'nombre', 'tipo'])
        self.vm_memoria_total = Gauge('proxmox_vm_memoria_total_bytes', 'Memoria total de la VM en bytes', ['nodo', 'vmid', 'nombre', 'tipo'])
        self.vm_memoria_usada = Gauge('proxmox_vm_memoria_usada_bytes', 'Memoria usada de la VM en bytes', ['nodo', 'vmid', 'nombre', 'tipo'])
        self.vm_uptime = Gauge('proxmox_vm_uptime_segundos', 'Tiempo de actividad de la VM en segundos', ['nodo', 'vmid', 'nombre', 'tipo'])
        self.vm_disco_lectura = Gauge('proxmox_vm_disco_lectura_bytes', 'Lectura de disco de la VM en bytes', ['nodo', 'vmid', 'nombre', 'tipo'])
        self.vm_disco_escritura = Gauge('proxmox_vm_disco_escritura_bytes', 'Escritura de disco de la VM en bytes', ['nodo', 'vmid', 'nombre', 'tipo'])
        self.vm_red_entrada = Gauge('proxmox_vm_red_entrada_bytes', 'Tráfico de red entrante de la VM en bytes', ['nodo', 'vmid', 'nombre', 'tipo'])
        self.vm_red_salida = Gauge('proxmox_vm_red_salida_bytes', 'Tráfico de red saliente de la VM en bytes', ['nodo', 'vmid', 'nombre', 'tipo'])
        
        # Métricas de almacenamiento
        self.almacenamiento_total = Gauge('proxmox_almacenamiento_total_bytes', 'Almacenamiento total en bytes', ['nodo', 'almacenamiento'])
        self.almacenamiento_usado = Gauge('proxmox_almacenamiento_usado_bytes', 'Almacenamiento usado en bytes', ['nodo', 'almacenamiento'])
        self.almacenamiento_disponible = Gauge('proxmox_almacenamiento_disponible_bytes', 'Almacenamiento disponible en bytes', ['nodo', 'almacenamiento'])
        
        # Contador de errores
        self.errores_recoleccion = Counter('proxmox_exportador_errores_recoleccion_total', 'Número total de errores de recolección')
    
    def recolectar_metricas_nodos(self):
        """Recolecta métricas para todos los nodos"""
        try:
            nodos = self.proxmox_service.get_nodes()
            
            for nodo in nodos:
                nombre_nodo = nodo['node']
                estado = nodo.get('status', '')
                
                # Establecer estado del nodo
                self.nodo_activo.labels(nodo=nombre_nodo).set(1 if estado == 'online' else 0)
                
                try:
                    # Obtener estado detallado del nodo
                    estado_nodo = self.proxmox_service.proxmox.nodes(nombre_nodo).status.get()
                    
                    # Uso de CPU (convertir a ratio 0-1)
                    if 'cpu' in estado_nodo:
                        self.nodo_uso_cpu.labels(nodo=nombre_nodo).set(estado_nodo['cpu'] / 100)
                    
                    # Métricas de memoria
                    if 'memory' in estado_nodo:
                        self.nodo_memoria_total.labels(nodo=nombre_nodo).set(estado_nodo['memory']['total'])
                        self.nodo_memoria_usada.labels(nodo=nombre_nodo).set(estado_nodo['memory']['used'])
                        self.nodo_memoria_libre.labels(nodo=nombre_nodo).set(estado_nodo['memory']['free'])
                    
                    # Tiempo de actividad
                    if 'uptime' in estado_nodo:
                        self.nodo_uptime.labels(nodo=nombre_nodo).set(estado_nodo['uptime'])
                    
                    # Obtener información de almacenamiento
                    try:
                        almacenamientos = self.proxmox_service.proxmox.nodes(nombre_nodo).storage.get()
                        for almacenamiento in almacenamientos:
                            nombre_almacenamiento = almacenamiento['storage']
                            
                            if 'total' in almacenamiento and 'used' in almacenamiento and 'avail' in almacenamiento:
                                # Convertir a bytes si es necesario (los valores pueden estar en KB)
                                total = almacenamiento['total']
                                usado = almacenamiento['used']
                                disponible = almacenamiento['avail']
                                
                                # Verificar si los valores necesitan ser convertidos a bytes (si están en KB)
                                if 'content' in almacenamiento and not almacenamiento.get('type') == 'zfspool':
                                    total *= 1024
                                    usado *= 1024
                                    disponible *= 1024
                                
                                self.almacenamiento_total.labels(nodo=nombre_nodo, almacenamiento=nombre_almacenamiento).set(total)
                                self.almacenamiento_usado.labels(nodo=nombre_nodo, almacenamiento=nombre_almacenamiento).set(usado)
                                self.almacenamiento_disponible.labels(nodo=nombre_nodo, almacenamiento=nombre_almacenamiento).set(disponible)
                    except Exception as e:
                        logger.error(f"Error al recolectar métricas de almacenamiento para el nodo {nombre_nodo}: {str(e)}")
                        self.errores_recoleccion.inc()
                    
                except Exception as e:
                    logger.error(f"Error al recolectar métricas detalladas para el nodo {nombre_nodo}: {str(e)}")
                    self.errores_recoleccion.inc()
        
        except Exception as e:
            logger.error(f"Error al recolectar métricas de nodos: {str(e)}")
            self.errores_recoleccion.inc()
    
    def recolectar_metricas_vms(self):
        """Recolecta métricas para todas las VMs"""
        try:
            # Obtener todas las VMs de todos los nodos
            vms = self.proxmox_service.get_vms()
            
            for vm in vms:
                try:
                    nombre_nodo = vm['node']
                    vmid = vm['vmid']
                    nombre_vm = vm.get('name', f"vm-{vmid}")
                    tipo_vm = vm.get('type', 'qemu')
                    estado_vm = vm.get('status', '')
                    
                    # Establecer estado de la VM
                    self.vm_activa.labels(
                        nodo=nombre_nodo, 
                        vmid=vmid, 
                        nombre=nombre_vm, 
                        tipo=tipo_vm
                    ).set(1 if estado_vm == 'running' else 0)
                    
                    # Solo recolectar métricas detalladas para VMs en ejecución
                    if estado_vm == 'running':
                        # Obtener estado detallado de la VM
                        try:
                            if tipo_vm == 'qemu':
                                estado_detallado = self.proxmox_service.get_vm_status(nombre_nodo, vmid, 'qemu')
                            else:  # lxc
                                estado_detallado = self.proxmox_service.get_vm_status(nombre_nodo, vmid, 'lxc')
                            
                            # Uso de CPU
                            if 'cpu' in estado_detallado:
                                self.vm_uso_cpu.labels(
                                    nodo=nombre_nodo, 
                                    vmid=vmid, 
                                    nombre=nombre_vm, 
                                    tipo=tipo_vm
                                ).set(estado_detallado['cpu'] / 100)  # Convertir a ratio 0-1
                            
                            # Memoria
                            if 'mem' in estado_detallado and 'maxmem' in estado_detallado:
                                self.vm_memoria_total.labels(
                                    nodo=nombre_nodo, 
                                    vmid=vmid, 
                                    nombre=nombre_vm, 
                                    tipo=tipo_vm
                                ).set(estado_detallado['maxmem'])
                                
                                self.vm_memoria_usada.labels(
                                    nodo=nombre_nodo, 
                                    vmid=vmid, 
                                    nombre=nombre_vm, 
                                    tipo=tipo_vm
                                ).set(estado_detallado['mem'])
                            
                            # Tiempo de actividad
                            if 'uptime' in estado_detallado:
                                self.vm_uptime.labels(
                                    nodo=nombre_nodo, 
                                    vmid=vmid, 
                                    nombre=nombre_vm, 
                                    tipo=tipo_vm
                                ).set(estado_detallado['uptime'])
                            
                            # E/S de disco
                            if 'diskread' in estado_detallado and 'diskwrite' in estado_detallado:
                                self.vm_disco_lectura.labels(
                                    nodo=nombre_nodo, 
                                    vmid=vmid, 
                                    nombre=nombre_vm, 
                                    tipo=tipo_vm
                                ).set(estado_detallado['diskread'])
                                
                                self.vm_disco_escritura.labels(
                                    nodo=nombre_nodo, 
                                    vmid=vmid, 
                                    nombre=nombre_vm, 
                                    tipo=tipo_vm
                                ).set(estado_detallado['diskwrite'])
                            
                            # Red
                            if 'netin' in estado_detallado and 'netout' in estado_detallado:
                                # Para redes, necesitamos sumar todas las interfaces
                                netin_total = 0
                                netout_total = 0
                                
                                if isinstance(estado_detallado['netin'], dict):
                                    for _, valor in estado_detallado['netin'].items():
                                        netin_total += valor
                                else:
                                    netin_total = estado_detallado['netin']
                                
                                if isinstance(estado_detallado['netout'], dict):
                                    for _, valor in estado_detallado['netout'].items():
                                        netout_total += valor
                                else:
                                    netout_total = estado_detallado['netout']
                                
                                self.vm_red_entrada.labels(
                                    nodo=nombre_nodo, 
                                    vmid=vmid, 
                                    nombre=nombre_vm, 
                                    tipo=tipo_vm
                                ).set(netin_total)
                                
                                self.vm_red_salida.labels(
                                    nodo=nombre_nodo, 
                                    vmid=vmid, 
                                    nombre=nombre_vm, 
                                    tipo=tipo_vm
                                ).set(netout_total)
                        
                        except Exception as e:
                            logger.error(f"Error al recolectar métricas detalladas para la VM {vmid} en el nodo {nombre_nodo}: {str(e)}")
                            self.errores_recoleccion.inc()
                
                except Exception as e:
                    logger.error(f"Error al procesar la VM: {str(e)}")
                    self.errores_recoleccion.inc()
        
        except Exception as e:
            logger.error(f"Error al recolectar métricas de VMs: {str(e)}")
            self.errores_recoleccion.inc()
    
    def iniciar(self):
        """Inicia el servidor HTTP para exponer las métricas y comienza la recolección periódica"""
        # Iniciar servidor HTTP
        start_http_server(self.puerto)
        logger.info(f"Servidor de métricas iniciado en el puerto {self.puerto}")
        
        while True:
            try:
                # Recolectar todas las métricas
                self.recolectar_metricas_nodos()
                self.recolectar_metricas_vms()
                logger.info("Métricas recolectadas correctamente")
            except Exception as e:
                logger.error(f"Error durante la recolección de métricas: {str(e)}")
                self.errores_recoleccion.inc()
            
            # Esperar hasta el próximo ciclo de recolección
            time.sleep(self.intervalo_segundos)

# Crear una instancia del exportador (no inicia automáticamente)
exportador_proxmox = ExportadorProxmox()