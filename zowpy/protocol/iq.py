"""
Async IQ Handler - Handler de IQ totalmente assíncrono.

Processa IQs de forma assíncrona.
"""

import asyncio
from typing import Dict, Callable, Optional
from loguru import logger

from zowpy.protocol.entities import IqProtocolEntity
from zowpy.protocol.structs import ProtocolNode

from ..core.events import AsyncEventEmitter


class AsyncIQHandler:
    """
    Handler de IQ totalmente assíncrono.
    Processa IQs de forma assíncrona.
    """
    
    def __init__(self, events: AsyncEventEmitter):
        self.events = events
        self._callbacks: Dict[str, Callable] = {}
        self._callbacks_lock = asyncio.Lock()
    
    async def handle_iq(self, iq_data: bytes) -> None:
        """
        Processa IQ de forma totalmente assíncrona.
        
        Args:
            iq_data: Dados do IQ
        """
        # Deserializa IQ
        iq = await self._deserialize_iq(iq_data)
        
        # Verifica se há callback registrado
        iq_id = iq.get("id")
        if iq_id:
            async with self._callbacks_lock:
                callback = self._callbacks.pop(iq_id, None)
            
            if callback:
                if asyncio.iscoroutinefunction(callback):
                    await callback(iq)
                else:
                    logger.info(f"Callback não é assíncrono: {callback}")
                    await asyncio.to_thread(callback(iq))
        
        # Emite evento
        await self.events.emit("iq", iq)
    
    async def register_callback(self, iq_id: str, callback: Callable) -> None:
        """
        Registra callback para IQ de forma assíncrona.
        
        Args:
            iq_id: ID do IQ
            callback: Callback para chamar
        """
        async with self._callbacks_lock:
            self._callbacks[iq_id] = callback
    
    async def _deserialize_iq(self, data: bytes) -> dict:
        """Deserializa IQ (pode ser síncrono)"""
        # Implementação específica
        return {"data": data}


class AppSyncStateIqProtocolEntity(IqProtocolEntity):

        
    '''
        <iq to='s.whatsapp.net' xmlns='w:sync:app:state' type='set' id='0d'>
            <sync data_namespace='3'>
                <collection name='critical_unblock_low' order='0'>
                    <patch>
                        EtkBCAAS1AEKIgogq1KjkZ0di/MjsxXUWlhl3kX3QGdMpDDX7vlM7opusQ0SowEKoAGGa8or/ieTjIehj/fR1vsP/dMSTEP9SqeckQ4fDJPi2JrIk8ZdOCHzCP7v4iwfCTyEJyk2bVbeXq+vwumzbPTxoqpuc/wrqMGv91YepCHFvyABBV2mEcnHla3nGZb2BZs8FYWge9dz5J/edB4Mxeiv4nNgWiBGTOrMyJPW6FONvNl8UzaMHsoa8KWbQ5fRCI702IAW0i+t1j5t+4EAX1kvGggKBgAAAABoRSIgHAetpsGu+MQlxtXgu1ziyTrLj9SzYB0ACj4J6P79xJcqICDiRWvAbC/IDW/xy7Ve7uvE3WzauqQfa7Y/2rh+zxL0MggKBgAAAABoRUAA
                    </patch>
                </collection>
                <collection name='critical_block' order='1'>
                    <patch>
                        EpcBCAASkgEKIgog6ljOH0I5TnwqXIiRJKsnlDYWcQuFbKohxbjYU6I926QSYgpgDY23FQHEzkllChxoPp+rvHs/ijgOHFo43uVjyTMmX1vnXzBO9vGH6T/ZAg7EeQh8QV1t+utJldrMueqt20wzjLE7De2ODIhbwUFnzGTV5YGeD0GjvKsU1/nV2ZTgEw3CGggKBgAAAABoRRKnAQgAEqIBCiIKICsyUbZaTs/L4QCU5YK3Hcxl5rpJMzqrqV5qIV/SkmynEnIKcPQUhIZ2cqk5tDuyW9BkWO4pQu79WFKgRn588FkwTSmbgvmDhci0EsIP89L5Dd8bDJrxSRfl0Wkhr8gk7aGFlj7f6/LJVUAb3FjwniToUuIw12gakgnJyU/O7SctYtJ4QGblc0EXUGl3wcwdq3qss9MaCAoGAAAAAGhFIiA3UluNObBB/ToM1EMLH6eWtRThSZjQZhtZ6fu5xftRZSogvFA3mV2BbKu/tsEdiuTIQ4mG+LUK0lSECKYEYETlgvwyCAoGAAAAAGhFQAA=
                    </patch>
                </collection>
            </sync>
        </iq>

    '''

    def __init__(self, patches=None, _id = None):
        super(AppSyncStateIqProtocolEntity, self).__init__(xmlns="w:sync:app:state" , iq_id = _id, iq_type = "set",to="s.whatsapp.net")
        self.patches = patches

    def toProtocolTreeNode(self):
        node = super(AppSyncStateIqProtocolEntity, self).to_protocol_node()
        syncnode = ProtocolNode("sync",{"data_namespace":"3"})
        
        if self.patches is not None:
            idx = 0
            for name,patch in self.patches.items():
                collectionNode = ProtocolNode("collection",{"name":name,"order":str(idx)})
                idx +=1
                if patch is not None:
                    patchNode = ProtocolNode("patch", {}, [], patch.SerializeToString())
                    collectionNode.addChild(patchNode)                
                syncnode.addChild(collectionNode)        
        node.addChild(syncnode)      

        logger.debug(f"Node: {node}")
        logger.debug(f"syncnode: {syncnode}")
        logger.debug(f"self.patches : {self.patches }")
        return node    


