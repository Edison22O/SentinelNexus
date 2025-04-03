# sentinelnexus/proxmox_service.py
from proxmoxer import ProxmoxAPI
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class ProxmoxService:
    """
    Servicio para interactuar con la API de Proxmox VE
    """
    
    def __init__(self):
        """Inicializa la conexión con Proxmox usando los ajustes de settings.py"""
        try:
            self.proxmox = ProxmoxAPI(
                host=settings.PROXMOX['host'],
                user=settings.PROXMOX['user'],
                password=settings.PROXMOX['password'],
                verify_ssl=settings.PROXMOX['verify_ssl']
            )
            logger.info("Conexión establecida con Proxmox")
        except Exception as e:
            logger.error(f"Error al conectar con Proxmox: {str(e)}")
            self.proxmox = None
    
    def get_nodes(self):
        """Obtiene la lista de nodos (servidores físicos) en el cluster"""
        try:
            return self.proxmox.nodes.get()
        except Exception as e:
            logger.error(f"Error al obtener nodos: {str(e)}")
            return []
    
    def get_vms(self, node=None):
        """
        Obtiene la lista de VMs en todos los nodos o en un nodo específico
        
        Args:
            node (str, optional): Nombre del nodo. Si es None, se obtienen todas las VMs.
        
        Returns:
            list: Lista de máquinas virtuales
        """
        try:
            vms = []
            nodes = [node] if node else [n['node'] for n in self.get_nodes()]
            
            for node_name in nodes:
                # Obtener máquinas virtuales (qemu)
                node = self.proxmox.nodes(node_name)
                qemu_vms = node.qemu.get()
                for vm in qemu_vms:
                    vm['node'] = node_name
                    vm['type'] = 'qemu'
                vms.extend(qemu_vms)
                
                # Obtener contenedores (lxc)
                lxc_cts = node.lxc.get()
                for ct in lxc_cts:
                    ct['node'] = node_name
                    ct['type'] = 'lxc'
                vms.extend(lxc_cts)
                
            return vms
        except Exception as e:
            logger.error(f"Error al obtener VMs: {str(e)}")
            return []
    
    def get_vm_status(self, node, vmid, vm_type='qemu'):
        """
        Obtiene el estado de una VM específica
        
        Args:
            node (str): Nombre del nodo
            vmid (int): ID de la VM
            vm_type (str): Tipo de VM ('qemu' para KVM, 'lxc' para contenedores)
            
        Returns:
            dict: Estado de la VM
        """
        try:
            if vm_type == 'qemu':
                return self.proxmox.nodes(node).qemu(vmid).status.current.get()
            elif vm_type == 'lxc':
                return self.proxmox.nodes(node).lxc(vmid).status.current.get()
        except Exception as e:
            logger.error(f"Error al obtener estado de VM {vmid}: {str(e)}")
            return {}
    
    def start_vm(self, node, vmid, vm_type='qemu'):
        """Inicia una VM"""
        try:
            if vm_type == 'qemu':
                return self.proxmox.nodes(node).qemu(vmid).status.start.post()
            elif vm_type == 'lxc':
                return self.proxmox.nodes(node).lxc(vmid).status.start.post()
        except Exception as e:
            logger.error(f"Error al iniciar VM {vmid}: {str(e)}")
            return False
    
    def stop_vm(self, node, vmid, vm_type='qemu'):
        """Detiene una VM"""
        try:
            if vm_type == 'qemu':
                return self.proxmox.nodes(node).qemu(vmid).status.stop.post()
            elif vm_type == 'lxc':
                return self.proxmox.nodes(node).lxc(vmid).status.stop.post()
        except Exception as e:
            logger.error(f"Error al detener VM {vmid}: {str(e)}")
            return False
    
    def get_cluster_resources(self, resource_type=None):
        """
        Obtiene recursos del cluster (VMs, contenedores, almacenamiento, etc.)
        
        Args:
            resource_type (str, optional): Filtrar por tipo de recurso 
                (qemu, lxc, storage, node, etc.)
        
        Returns:
            list: Lista de recursos
        """
        try:
            params = {}
            if resource_type:
                params['type'] = resource_type
            return self.proxmox.cluster.resources.get(**params)
        except Exception as e:
            logger.error(f"Error al obtener recursos del cluster: {str(e)}")
            return []

# Instancia singleton para usar en toda la aplicación
proxmox_service = ProxmoxService()