"""
Servicio para gestionar Grafana desde Django
"""
import os
import subprocess
import shutil
import logging
from django.conf import settings
from pathlib import Path
import requests
import time
import json

logger = logging.getLogger(__name__)

class ServicioGrafana:
    """
    Servicio para gestionar la instancia de Grafana
    """
    
    def __init__(self):
        """Inicializa el servicio de Grafana"""
        self.base_dir = settings.BASE_DIR
        self.grafana_dir = Path(self.base_dir) / 'grafana'
        self.data_dir = self.grafana_dir / 'data'
        self.config_dir = self.grafana_dir / 'conf'
        self.logs_dir = self.grafana_dir / 'logs'
        self.dashboards_dir = self.grafana_dir / 'dashboards'
        self.process = None
        
        # URL y credenciales por defecto
        self.url = 'http://localhost:3000'
        self.usuario = 'admin'
        self.password = 'admin'
        
        # Asegurarse de que existan los directorios necesarios
        os.makedirs(self.grafana_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.dashboards_dir, exist_ok=True)
    
    def escribir_configuracion(self):
        """
        Escribe el archivo de configuración de Grafana
        """
        config = """
[server]
http_port = 3000
domain = localhost
root_url = %(protocol)s://%(domain)s:%(http_port)s/

[auth.anonymous]
enabled = true
org_name = Main Org.
org_role = Viewer

[security]
admin_user = admin
admin_password = admin
"""
        config_path = self.config_dir / 'grafana.ini'
        with open(config_path, 'w') as f:
            f.write(config)
        
        logger.info(f"Archivo de configuración de Grafana escrito en {config_path}")
        return config_path
    
    def iniciar(self):
        """
        Inicia el proceso de Grafana
        
        Returns:
            bool: True si se inició correctamente, False en caso contrario
        """
        try:
            # Verificar si existe el binario de Grafana
            grafana_bin = shutil.which('grafana-server')
            if not grafana_bin:
                logger.error("No se encontró el binario de Grafana. Asegúrate de que esté instalado y en PATH.")
                return False
            
            # Comprobar si ya existe un archivo de configuración, si no, crearlo
            config_path = self.config_dir / 'grafana.ini'
            if not os.path.exists(config_path):
                self.escribir_configuracion()
            
            # Construir comando para iniciar Grafana
            cmd = [
                grafana_bin,
                '--config', str(config_path),
                '--homepath', str(self.grafana_dir),
                f'cfg:default.paths.data={self.data_dir}',
                f'cfg:default.paths.logs={self.logs_dir}',
                f'cfg:default.paths.plugins={self.grafana_dir}/plugins'
            ]
            
            # Iniciar proceso en segundo plano
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            logger.info(f"Grafana iniciado con PID {self.process.pid}")
            
            # Esperar a que Grafana esté listo
            max_intentos = 30
            for intento in range(max_intentos):
                try:
                    response = requests.get(f"{self.url}/api/health")
                    if response.status_code == 200:
                        logger.info("Grafana está listo")
                        # Configurar la fuente de datos de Prometheus
                        self.configurar_datasource_prometheus()
                        # Importar dashboards predefinidos
                        self.importar_dashboards_predefinidos()
                        return True
                except:
                    pass
                
                time.sleep(1)
                if intento % 5 == 0:
                    logger.info(f"Esperando a que Grafana esté listo... Intento {intento+1}/{max_intentos}")
            
            logger.error("Grafana no respondió después de varios intentos")
            return False
        
        except Exception as e:
            logger.error(f"Error al iniciar Grafana: {str(e)}")
            return False
    
    def detener(self):
        """
        Detiene el proceso de Grafana
        
        Returns:
            bool: True si se detuvo correctamente, False en caso contrario
        """
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
                logger.info("Grafana detenido correctamente")
                self.process = None
                return True
            except Exception as e:
                logger.error(f"Error al detener Grafana: {str(e)}")
                try:
                    self.process.kill()
                    logger.info("Grafana terminado forzosamente")
                    self.process = None
                    return True
                except:
                    logger.error("No se pudo terminar el proceso de Grafana")
                    return False
        return True  # Ya estaba detenido
    
    def reiniciar(self):
        """
        Reinicia el proceso de Grafana
        
        Returns:
            bool: True si se reinició correctamente, False en caso contrario
        """
        self.detener()
        return self.iniciar()
    
    def verificar_estado(self):
        """
        Verifica si Grafana está en ejecución
        
        Returns:
            bool: True si está en ejecución, False en caso contrario
        """
        if self.process:
            returncode = self.process.poll()
            if returncode is None:
                try:
                    response = requests.get(f"{self.url}/api/health")
                    return response.status_code == 200
                except:
                    return False
            else:
                logger.warning(f"Grafana se detuvo con código de salida {returncode}")
                self.process = None
                return False
        return False
    
    def configurar_datasource_prometheus(self):
        """
        Configura Prometheus como fuente de datos en Grafana
        
        Returns:
            bool: True si se configuró correctamente, False en caso contrario
        """
        try:
            # Verificar si ya existe la fuente de datos
            response = requests.get(
                f"{self.url}/api/datasources/name/Prometheus",
                auth=(self.usuario, self.password)
            )
            
            if response.status_code == 200:
                logger.info("La fuente de datos Prometheus ya existe")
                return True
            
            # Configurar la fuente de datos
            datasource = {
                "name": "Prometheus",
                "type": "prometheus",
                "url": "http://localhost:9090",
                "access": "proxy",
                "isDefault": True
            }
            
            response = requests.post(
                f"{self.url}/api/datasources",
                json=datasource,
                auth=(self.usuario, self.password)
            )
            
            if response.status_code == 200:
                logger.info("Fuente de datos Prometheus configurada correctamente")
                return True
            else:
                logger.error(f"Error al configurar la fuente de datos: {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Error al configurar la fuente de datos: {str(e)}")
            return False
    
    def importar_dashboards_predefinidos(self):
        """
        Importa dashboards predefinidos para monitoreo de Proxmox
        
        Returns:
            bool: True si se importaron correctamente, False en caso contrario
        """
        try:
            # Crear el dashboard de resumen de Proxmox
            dashboard_proxmox = {
                "dashboard": {
                    "id": None,
                    "title": "Resumen de Proxmox",
                    "tags": ["proxmox", "sentinelnexus"],
                    "timezone": "browser",
                    "panels": [
                        {
                            "id": 1,
                            "title": "Uso de CPU por Nodo",
                            "type": "graph",
                            "datasource": "Prometheus",
                            "targets": [
                                {
                                    "expr": "proxmox_nodo_uso_cpu_ratio{nodo=~\"$nodo\"}",
                                    "legendFormat": "{{nodo}}",
                                    "refId": "A"
                                }
                            ],
                            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
                        },
                        {
                            "id": 2,
                            "title": "Uso de Memoria por Nodo",
                            "type": "graph",
                            "datasource": "Prometheus",
                            "targets": [
                                {
                                    "expr": "proxmox_nodo_memoria_usada_bytes{nodo=~\"$nodo\"} / proxmox_nodo_memoria_total_bytes{nodo=~\"$nodo\"}",
                                    "legendFormat": "{{nodo}}",
                                    "refId": "A"
                                }
                            ],
                            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
                        },
                        {
                            "id": 3,
                            "title": "Estado de Nodos",
                            "type": "stat",
                            "datasource": "Prometheus",
                            "targets": [
                                {
                                    "expr": "proxmox_nodo_activo{nodo=~\"$nodo\"}",
                                    "legendFormat": "{{nodo}}",
                                    "refId": "A"
                                }
                            ],
                            "options": {
                                "colorMode": "value",
                                "graphMode": "none",
                                "justifyMode": "auto",
                                "orientation": "horizontal",
                                "reduceOptions": {
                                    "calcs": ["lastNotNull"],
                                    "fields": "",
                                    "values": False
                                },
                                "textMode": "auto"
                            },
                            "mappings": [
                                {
                                    "type": "value",
                                    "options": {
                                        "0": {"text": "Inactivo", "color": "red"},
                                        "1": {"text": "Activo", "color": "green"}
                                    }
                                }
                            ],
                            "gridPos": {"h": 4, "w": 6, "x": 0, "y": 8}
                        },
                        {
                            "id": 4,
                            "title": "VMs Activas por Nodo",
                            "type": "bargauge",
                            "datasource": "Prometheus",
                            "targets": [
                                {
                                    "expr": "sum(proxmox_vm_activa{nodo=~\"$nodo\"}) by (nodo)",
                                    "legendFormat": "{{nodo}}",
                                    "refId": "A"
                                }
                            ],
                            "gridPos": {"h": 4, "w": 6, "x": 6, "y": 8}
                        }
                    ],
                    "templating": {
                        "list": [
                            {
                                "name": "nodo",
                                "type": "query",
                                "datasource": "Prometheus",
                                "query": "label_values(proxmox_nodo_activo, nodo)",
                                "regex": "",
                                "multi": True,
                                "includeAll": True
                            }
                        ]
                    },
                    "time": {
                        "from": "now-6h",
                        "to": "now"
                    },
                    "refresh": "1m",
                    "schemaVersion": 16,
                    "version": 1
                },
                "overwrite": True,
                "folderId": 0
            }
            
            # Dashboard para VMs
            dashboard_vms = {
                "dashboard": {
                    "id": None,
                    "title": "Detalles de Máquinas Virtuales",
                    "tags": ["proxmox", "sentinelnexus", "vms"],
                    "timezone": "browser",
                    "panels": [
                        {
                            "id": 1,
                            "title": "Uso de CPU por VM",
                            "type": "graph",
                            "datasource": "Prometheus",
                            "targets": [
                                {
                                    "expr": "proxmox_vm_uso_cpu_ratio{nombre=~\"$vm\"}",
                                    "legendFormat": "{{nombre}} ({{vmid}})",
                                    "refId": "A"
                                }
                            ],
                            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
                        },
                        {
                            "id": 2,
                            "title": "Uso de Memoria por VM",
                            "type": "graph",
                            "datasource": "Prometheus",
                            "targets": [
                                {
                                    "expr": "proxmox_vm_memoria_usada_bytes{nombre=~\"$vm\"} / proxmox_vm_memoria_total_bytes{nombre=~\"$vm\"}",
                                    "legendFormat": "{{nombre}} ({{vmid}})",
                                    "refId": "A"
                                }
                            ],
                            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
                        },
                        {
                            "id": 3,
                            "title": "Tráfico de Red - Entrada",
                            "type": "graph",
                            "datasource": "Prometheus",
                            "targets": [
                                {
                                    "expr": "rate(proxmox_vm_red_entrada_bytes{nombre=~\"$vm\"}[5m])",
                                    "legendFormat": "{{nombre}} ({{vmid}})",
                                    "refId": "A"
                                }
                            ],
                            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
                        },
                        {
                            "id": 4,
                            "title": "Tráfico de Red - Salida",
                            "type": "graph",
                            "datasource": "Prometheus",
                            "targets": [
                                {
                                    "expr": "rate(proxmox_vm_red_salida_bytes{nombre=~\"$vm\"}[5m])",
                                    "legendFormat": "{{nombre}} ({{vmid}})",
                                    "refId": "A"
                                }
                            ],
                            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
                        },
                        {
                            "id": 5,
                            "title": "E/S de Disco - Lectura",
                            "type": "graph",
                            "datasource": "Prometheus",
                            "targets": [
                                {
                                    "expr": "rate(proxmox_vm_disco_lectura_bytes{nombre=~\"$vm\"}[5m])",
                                    "legendFormat": "{{nombre}} ({{vmid}})",
                                    "refId": "A"
                                }
                            ],
                            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16}
                        },
                        {
                            "id": 6,
                            "title": "E/S de Disco - Escritura",
                            "type": "graph",
                            "datasource": "Prometheus",
                            "targets": [
                                {
                                    "expr": "rate(proxmox_vm_disco_escritura_bytes{nombre=~\"$vm\"}[5m])",
                                    "legendFormat": "{{nombre}} ({{vmid}})",
                                    "refId": "A"
                                }
                            ],
                            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16}
                        }
                    ],
                    "templating": {
                        "list": [
                            {
                                "name": "vm",
                                "type": "query",
                                "datasource": "Prometheus",
                                "query": "label_values(proxmox_vm_activa, nombre)",
                                "regex": "",
                                "multi": True,
                                "includeAll": True
                            }
                        ]
                    },
                    "time": {
                        "from": "now-6h",
                        "to": "now"
                    },
                    "refresh": "1m",
                    "schemaVersion": 16,
                    "version": 1
                },
                "overwrite": True,
                "folderId": 0
            }
            
            # Importar dashboards
            for dashboard_data in [dashboard_proxmox, dashboard_vms]:
                response = requests.post(
                    f"{self.url}/api/dashboards/db",
                    json=dashboard_data,
                    auth=(self.usuario, self.password)
                )
                
                if response.status_code == 200:
                    dashboard_url = response.json()['url']
                    logger.info(f"Dashboard importado correctamente: {dashboard_url}")
                else:
                    logger.error(f"Error al importar dashboard: {response.text}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error al importar dashboards predefinidos: {str(e)}")
            return False