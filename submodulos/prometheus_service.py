"""
Servicio para gestionar Prometheus desde Django
"""
import os
import subprocess
import shutil
import logging
from django.conf import settings
from pathlib import Path

logger = logging.getLogger(__name__)

class ServicioPrometheus:
    """
    Servicio para gestionar la instancia de Prometheus
    """
    
    def __init__(self):
        """Inicializa el servicio de Prometheus"""
        self.base_dir = settings.BASE_DIR
        self.prometheus_dir = Path(self.base_dir) / 'prometheus'
        self.config_path = self.prometheus_dir / 'prometheus.yml'
        self.data_dir = self.prometheus_dir / 'data'
        self.process = None
        
        # Asegurarse de que existan los directorios necesarios
        os.makedirs(self.prometheus_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
    
    def escribir_configuracion(self, targets=None, intervalo='15s'):
        """
        Escribe el archivo de configuración de Prometheus
        
        Args:
            targets (list): Lista de objetivos para scraping (por defecto, localhost:9090)
            intervalo (str): Intervalo de scraping
        """
        if targets is None:
            targets = ['localhost:9090']
        
        config = f"""
# Configuración global de Prometheus
global:
  scrape_interval: {intervalo}
  evaluation_interval: {intervalo}

# Configuración de reglas de alertas
rule_files:
  # - "reglas/*.yml"

# Configuración de jobs de scraping
scrape_configs:
  - job_name: 'proxmox'
    static_configs:
      - targets: {targets}
    
  - job_name: 'django'
    static_configs:
      - targets: ['localhost:8000']

  # Job para autoscraping de Prometheus
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
"""
        with open(self.config_path, 'w') as f:
            f.write(config)
        
        logger.info(f"Archivo de configuración de Prometheus escrito en {self.config_path}")
        return self.config_path
    
    def iniciar(self):
        """
        Inicia el proceso de Prometheus
        
        Returns:
            bool: True si se inició correctamente, False en caso contrario
        """
        try:
            # Verificar si existe el binario de Prometheus
            prometheus_bin = shutil.which('prometheus')
            if not prometheus_bin:
                logger.error("No se encontró el binario de Prometheus. Asegúrate de que esté instalado y en PATH.")
                return False
            
            # Comprobar si ya existe un archivo de configuración, si no, crearlo
            if not os.path.exists(self.config_path):
                self.escribir_configuracion()
            
            # Construir comando para iniciar Prometheus
            cmd = [
                prometheus_bin,
                '--config.file', str(self.config_path),
                '--storage.tsdb.path', str(self.data_dir),
                '--web.console.templates', str(self.prometheus_dir / 'consoles'),
                '--web.console.libraries', str(self.prometheus_dir / 'console_libraries')
            ]
            
            # Iniciar proceso en segundo plano
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            logger.info(f"Prometheus iniciado con PID {self.process.pid}")
            return True
        
        except Exception as e:
            logger.error(f"Error al iniciar Prometheus: {str(e)}")
            return False
    
    def detener(self):
        """
        Detiene el proceso de Prometheus
        
        Returns:
            bool: True si se detuvo correctamente, False en caso contrario
        """
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
                logger.info("Prometheus detenido correctamente")
                self.process = None
                return True
            except Exception as e:
                logger.error(f"Error al detener Prometheus: {str(e)}")
                try:
                    self.process.kill()
                    logger.info("Prometheus terminado forzosamente")
                    self.process = None
                    return True
                except:
                    logger.error("No se pudo terminar el proceso de Prometheus")
                    return False
        return True  # Ya estaba detenido
    
    def reiniciar(self):
        """
        Reinicia el proceso de Prometheus
        
        Returns:
            bool: True si se reinició correctamente, False en caso contrario
        """
        self.detener()
        return self.iniciar()
    
    def verificar_estado(self):
        """
        Verifica si Prometheus está en ejecución
        
        Returns:
            bool: True si está en ejecución, False en caso contrario
        """
        if self.process:
            returncode = self.process.poll()
            if returncode is None:
                return True  # Proceso en ejecución
            else:
                logger.warning(f"Prometheus se detuvo con código de salida {returncode}")
                self.process = None
                return False
        return False

# Instancia singleton para usar en toda la aplicación
servicio_prometheus = ServicioPrometheus()