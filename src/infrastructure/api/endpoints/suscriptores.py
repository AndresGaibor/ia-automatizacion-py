from typing import List, Dict, Any, Union, Optional
from ..client import APIClient
from ..decorators import medium_rate_limit, burst_rate_limit
from ..models.suscriptores import (
    ListSummary, ListStats, ListFields, SubscriberDetails,
    SubscriberSearchResult, SubscriberList, ListSubsStats,
    FormsList, SegmentsList, FieldType, BatchAddResult,
    InactiveSubscribersList, FieldsList, MergeFieldsList,
    SubscriberData, BatchDeleteResult, ActualSubscriber
)


class SuscriptoresAPI:
    """Endpoints relacionados con suscriptores y listas"""

    def __init__(self, client: APIClient):
        self.client = client

    # === GESTIÓN DE LISTAS ===

    def create_list(
        self,
        sender_email: str,
        name: str,
        company: str,
        country: str,
        city: str,
        address: str,
        phone: str
    ) -> int:
        """
        Crea una nueva lista de suscriptores.

        Args:
            sender_email: Email del remitente
            name: Nombre de la lista
            company: Empresa
            country: País
            city: Ciudad
            address: Dirección
            phone: Teléfono

        Returns:
            int: ID de la lista creada
        """
        data = {
            "sender_email": sender_email,
            "name": name,
            "company": company,
            "country": country,
            "city": city,
            "address": address,
            "phone": phone
        }

        response = self.client.post("createList/", data=data)

        # La API puede retornar diferentes formatos
        if isinstance(response, int):
            return response
        elif isinstance(response, dict):
            # Puede ser {"id": 123} o {"list_id": "123"}
            if "id" in response:
                return int(response["id"])
            elif "list_id" in response:
                return int(response["list_id"])
        elif isinstance(response, str) and response.isdigit():
            return int(response)

        raise ValueError(f"Respuesta inesperada de la API: {response}")

    @burst_rate_limit
    def get_lists(self) -> List[ListSummary]:
        """
        Obtiene las listas de suscriptores disponibles.

        Returns:
            List[ListSummary]: Lista de resúmenes de listas

        Rate limit: 5 peticiones/segundo
        """
        response = self.client.get("getLists/")
        # Asegurar que la respuesta sea procesada correctamente
        if isinstance(response, dict):
            result: List[ListSummary] = ListSummary.from_api_response(response)
            return result
        else:
            # Fallback para respuestas inesperadas
            empty_result: List[ListSummary] = []
            return empty_result

    @medium_rate_limit
    def get_list_stats(self, list_id: int) -> ListStats:
        """
        Obtiene datos generales sobre la lista.

        Args:
            list_id: ID de la lista

        Returns:
            ListStats: Estadísticas de la lista

        Rate limit: 10 peticiones/minuto
        """
        params = {"list_id": list_id}
        response = self.client.get("getListStats/", params=params)
        return ListStats.from_api_response(response)

    @medium_rate_limit
    def get_list_subs_stats(self, list_id: int, block_index: int = 0) -> ListSubsStats:
        """
        Obtiene datos de las campañas enviadas a cada suscriptor de la lista.

        Args:
            list_id: ID de la lista
            block_index: Índice de paginación

        Returns:
            ListSubsStats: Estadísticas por suscriptor

        Rate limit: 10 peticiones/minuto
        """
        params = {"list_id": list_id, "block_index": block_index}
        response = self.client.get("getListSubsStats/", params=params)
        return ListSubsStats.from_api_response(response)

    # === GESTIÓN DE SUSCRIPTORES ===

    def add_subscriber(
        self,
        list_id: int,
        merge_fields: Dict[str, Any],
        double_optin: int = 1,
        update_subscriber: int = 0,
        complete_json: int = 0
    ) -> int:
        """
        Agrega un suscriptor a una lista.

        Args:
            list_id: ID de la lista
            merge_fields: Campos del suscriptor (debe incluir 'email')
                         NOTA: Para segmentos usar 'Segmentos' (con S mayúscula)
            double_optin: Activar doble opt-in (1=sí, 0=no)
            update_subscriber: Actualizar si existe (1=sí, 0=no)
            complete_json: Respuesta completa (1=sí, 0=no)

        Returns:
            int: ID del suscriptor

        Raises:
            ValueError: Si merge_fields no contiene email o usa nombres incorrectos
        """
        if "email" not in merge_fields:
            raise ValueError("merge_fields debe contener el campo 'email'")
        
        # Validaciones específicas para campos problemáticos
        self._validate_merge_fields(merge_fields, list_id)

        # Preparar datos base
        data = {
            "list_id": list_id,
            "double_optin": double_optin,
            "update_subscriber": update_subscriber,
            "complete_json": complete_json
        }

        # Agregar merge_fields con el formato correcto: merge_fields[campo]=valor
        for field_name, field_value in merge_fields.items():
            data[f"merge_fields[{field_name}]"] = field_value

        response = self.client.post("addSubscriber/", data=data)

        # La API puede retornar diferentes formatos
        if isinstance(response, int):
            return response
        elif isinstance(response, dict):
            # Puede ser {"id": 123}, {"subscriber_id": "123"}, etc.
            for key in ["id", "subscriber_id", "user_id"]:
                if key in response:
                    return int(response[key])
        elif isinstance(response, str) and response.isdigit():
            return int(response)

        raise ValueError(f"Respuesta inesperada de la API: {response}")
    
    def _validate_merge_fields(self, merge_fields: Dict[str, Any], list_id: int) -> None:
        """
        Valida que los merge_fields usen nombres correctos según la lista específica.
        
        Args:
            merge_fields: Campos a validar
            list_id: ID de la lista (para validaciones específicas)
            
        Raises:
            ValueError: Si encuentra nombres incorrectos de campos
        """
        # Validaciones específicas para lista 1168867 (Prueba_SEGMENTOS)
        if list_id == 1168867:
            # Verificar campo de segmentos
            segment_fields = [k for k in merge_fields.keys() if 'segment' in k.lower()]
            if segment_fields:
                incorrect_fields = [f for f in segment_fields if f not in ['Segmentos', 'SEGMENTOS']]
                if incorrect_fields:
                    raise ValueError(
                        f"Campo(s) de segmento incorrecto(s): {incorrect_fields}. "
                        f"Use 'Segmentos' (con S mayúscula) para lista {list_id}"
                    )
        
        # Validaciones generales
        common_mistakes = {
            'segmento': 'Segmentos',
            'segmentos': 'Segmentos', 
            'segment': 'Segmentos',
            'segments': 'Segmentos'
        }
        
        for incorrect, correct in common_mistakes.items():
            if incorrect in merge_fields:
                raise ValueError(
                    f"Campo '{incorrect}' incorrecto. Use '{correct}' en su lugar. "
                    f"Los nombres de campos son sensibles a mayúsculas."
                )

    def unsubscribe_subscriber(self, list_id: int, email: str) -> None:
        """
        Da de baja un suscriptor de una lista.

        Args:
            list_id: ID de la lista
            email: Email del suscriptor
        """
        data = {"list_id": list_id, "email": email}
        self.client.post("unsubscribeSubscriber/", data=data)

    @burst_rate_limit
    def batch_add_subscribers(
        self,
        list_id: int,
        subscribers_data: List[SubscriberData],
        update_subscriber: int = 0,
        complete_json: int = 0
    ) -> BatchAddResult:
        """
        Agrega múltiples suscriptores a una lista de una vez.

        Args:
            list_id: ID de la lista
            subscribers_data: Lista de SubscriberData (datos tipados de suscriptores)
            update_subscriber: Actualizar si existe (1=sí, 0=no)
            complete_json: Respuesta completa (1=sí, 0=no)

        Returns:
            BatchAddResult: Resultados del proceso de agregado masivo

        Rate limit: 5 peticiones/segundo

        Raises:
            ValueError: Si hay más de 1000 suscriptores
        """
        # Validar los datos de entrada
        if len(subscribers_data) > 1000:
            raise ValueError("Máximo 1000 suscriptores por lote")

        import json

        # Convertir SubscriberData a diccionarios
        subscribers_dict = [subscriber.model_dump() for subscriber in subscribers_data]

        data = {
            "list_id": list_id,
            "subscribers_data": json.dumps(subscribers_dict),
            "update_subscriber": update_subscriber,
            "complete_json": complete_json
        }

        response = self.client.post("batchAddSubscribers/", data=data)
        return BatchAddResult.from_api_response(response)

    def delete_subscriber(self, list_id: int, email: str) -> None:
        """
        Elimina un suscriptor específico de una lista.

        ADVERTENCIA: Esta operación elimina permanentemente el suscriptor.

        Args:
            list_id: ID de la lista
            email: Email del suscriptor a eliminar
        """
        data = {"list_id": list_id, "email": email}
        self.client.post("deleteSubscriber/", data=data)

    # === BÚSQUEDA Y CONSULTA ===

    @medium_rate_limit
    def get_subscribers(
        self,
        list_id: int,
        status: Optional[int] = None,  # CORREGIDO: status=1 no funciona, debe ser None, 0 o 5
        block_index: int = 0,
        all_fields: int = 1,  # CORREGIDO: por defecto 1 para obtener todos los campos
        complete_json: int = 1  # CORREGIDO: por defecto 1 según documentación
    ) -> List[ActualSubscriber]:
        """
        Obtiene los suscriptores de una lista.

        Args:
            list_id: ID de la lista
            status: Estado del suscriptor (None=todos, 0=todos activos, 5=también funciona)
                   NOTA: status=1 NO FUNCIONA según pruebas de API
            block_index: Índice de paginación
            all_fields: Todos los campos (1=sí, 0=no) - recomendado 1
            complete_json: Respuesta completa (1=sí, 0=no) - recomendado 1

        Returns:
            List[ActualSubscriber]: Lista de suscriptores (retorna directamente lista, no objeto wrapper)

        Rate limit: 10 peticiones/minuto
        
        Raises:
            HTTPError: Si status=1,2,3,4 (valores que no funcionan según pruebas)
        """
        params = {
            "list_id": list_id,
            "block_index": block_index,
            "all_fields": all_fields,
            "complete_json": complete_json
        }
        
        # Solo agregar status si se especifica (None = usar defecto de API)
        if status is not None:
            if status in [1, 2, 3, 4]:
                raise ValueError(f"status={status} no funciona con esta API. Use None, 0, o 5")
            params["status"] = status
            
        response = self.client.get("getSubscribers/", params=params)
        return SubscriberList.from_api_response(response)

    @burst_rate_limit
    def get_subscriber_details(self, list_id: int, subscriber: str) -> SubscriberDetails:
        """
        Obtiene datos avanzados de un suscriptor.

        Args:
            list_id: ID de la lista
            subscriber: Email del suscriptor

        Returns:
            SubscriberDetails: Detalles del suscriptor

        Rate limit: 5 peticiones/segundo
        """
        params = {"list_id": list_id, "subscriber": subscriber}
        response = self.client.get("getSubscriberDetails/", params=params)
        return SubscriberDetails.from_api_response(response)

    @medium_rate_limit
    def search_subscriber(self, subscriber: str) -> List[ActualSubscriber]:
        """
        Devuelve los datos avanzados de un suscriptor en cada lista a la que pertenezca.

        Args:
            subscriber: Email a buscar

        Returns:
            List[ActualSubscriber]: Datos del suscriptor en todas las listas
                                   (retorna directamente lista, no objeto wrapper)

        Rate limit: 10 peticiones/minuto
        """
        params = {"subscriber": subscriber}
        response = self.client.get("searchSubscriber/", params=params)
        return SubscriberSearchResult.from_api_response(response)

    @medium_rate_limit
    def get_inactive_subscribers(
        self,
        date_from: str,
        date_to: str,
        full_info: int = 0
    ) -> InactiveSubscribersList:
        """
        Obtiene suscriptores inactivos en un rango de fechas.

        Args:
            date_from: Fecha desde (formato YYYY-MM-DD)
            date_to: Fecha hasta (formato YYYY-MM-DD)
            full_info: Información completa (1=sí, 0=no)

        Returns:
            InactiveSubscribersList: Lista de suscriptores inactivos

        Rate limit: 10 peticiones/minuto
        """
        params = {
            "date_from": date_from,
            "date_to": date_to,
            "full_info": full_info
        }
        response = self.client.get("getInactiveSubscribers/", params=params)
        return InactiveSubscribersList.from_api_response(response, date_from, date_to)

    # === CAMPOS PERSONALIZADOS ===

    @medium_rate_limit
    def add_merge_tag(self, list_id: int, field_name: str, field_type: Union[str, FieldType]) -> None:
        """
        Añade un campo a una lista.

        Args:
            list_id: ID de la lista
            field_name: Nombre del campo
            field_type: Tipo del campo (text, number, date, etc.)

        Rate limit: 10 peticiones/minuto
        """
        # Convertir enum a string si es necesario
        if isinstance(field_type, FieldType):
            field_type_str = field_type.value
        else:
            field_type_str = field_type

        data = {
            "list_id": list_id,
            "field_name": field_name,
            "field_type": field_type_str
        }
        self.client.post("addMergeTag/", data=data)

    def get_list_fields(self, list_id: int) -> ListFields:
        """
        Obtiene toda la información de los campos de una lista como el valor,
        el tipo o la visibilidad, en formato JSON.

        Args:
            list_id: ID de la lista

        Returns:
            ListFields: Información completa de campos
        """
        params = {"list_id": list_id}
        response = self.client.get("getListFields/", params=params)
        return ListFields.from_api_response(response)

    @medium_rate_limit
    def get_fields(self, list_id: int) -> FieldsList:
        """
        Obtiene campos y tipos de una lista.

        Args:
            list_id: ID de la lista

        Returns:
            FieldsList: Campos y tipos disponibles

        Rate limit: 10 peticiones/minuto
        """
        params = {"list_id": list_id}
        response = self.client.get("getFields/", params=params)
        return FieldsList.from_api_response(response)

    @medium_rate_limit
    def get_merge_fields(self, list_id: int) -> MergeFieldsList:
        """
        Obtiene merge fields de una lista.

        Args:
            list_id: ID de la lista

        Returns:
            MergeFieldsList: Merge fields disponibles

        Rate limit: 10 peticiones/minuto
        """
        params = {"list_id": list_id}
        response = self.client.get("getMergeFields/", params=params)
        return MergeFieldsList.from_api_response(response)

    # === OTROS ===

    @burst_rate_limit
    def get_forms(self, list_id: int) -> FormsList:
        """
        Obtiene los formularios asociados a una lista.

        Args:
            list_id: ID de la lista

        Returns:
            FormsList: Formularios asociados

        Rate limit: 5 peticiones/segundo
        """
        params = {"list_id": list_id}
        response = self.client.get("getForms/", params=params)
        return FormsList.from_api_response(response)

    def get_list_segments(self, list_id: int) -> SegmentsList:
        """
        Obtiene los segmentos de una lista.

        Args:
            list_id: ID de la lista

        Returns:
            SegmentsList: Segmentos de la lista
        """
        params = {"list_id": list_id}
        response = self.client.get("getListSegments/", params=params)
        return SegmentsList.from_api_response(response)

    # === MÉTODOS DE ELIMINACIÓN ===

    @medium_rate_limit
    def batch_delete_subscribers(self, list_id: int, email_list: Dict[str, str]) -> BatchDeleteResult:
        """
        Elimina un grupo de suscriptores de una lista.

        ADVERTENCIA: Esta operación elimina permanentemente los suscriptores.
        ⚠️  REQUIERE CONFIRMACIÓN MANUAL ANTES DE USAR

        Args:
            list_id: ID de la lista
            email_list: Dict con lista de emails a eliminar

        Returns:
            BatchDeleteResult: Resultados del proceso de eliminación

        Rate limit: 10 peticiones/minuto
        """
        data = {
            "list_id": list_id,
            "email_list": email_list
        }

        response = self.client.post("batchDeleteSubscribers/", data=data)
        return BatchDeleteResult.from_api_response(response)

    def update_subscriber(
        self,
        list_id: int,
        subscriber_id: int,
        merge_fields: Dict[str, Any],
        update_on_duplicate: int = 1
    ) -> int:
        """
        Actualiza un suscriptor existente.

        Args:
            list_id: ID de la lista
            subscriber_id: ID del suscriptor
            merge_fields: Campos a actualizar
                         NOTA: Para segmentos usar 'Segmentos' (con S mayúscula)
            update_on_duplicate: Actualizar en caso de duplicado (1=sí, 0=no)

        Returns:
            int: ID del suscriptor actualizado

        Raises:
            ValueError: Si los merge_fields contienen nombres incorrectos
        """
        # Validar nombres de campos antes de enviar
        self._validate_merge_fields(merge_fields, list_id)

        data = {
            "list_id": list_id,
            "subscriber_id": subscriber_id,
            "update_on_duplicate": update_on_duplicate
        }

        # Agregar merge_fields
        for field_name, field_value in merge_fields.items():
            data[f"merge_fields[{field_name}]"] = field_value

        response = self.client.post("updateSubscriber/", data=data)

        # Procesar respuesta similar a add_subscriber
        if isinstance(response, int):
            return response
        elif isinstance(response, dict):
            for key in ["id", "subscriber_id", "user_id"]:
                if key in response:
                    return int(response[key])
        elif isinstance(response, str) and response.isdigit():
            return int(response)

        raise ValueError(f"Respuesta inesperada de la API: {response}")

    @medium_rate_limit
    def delete_list(self, list_id: int) -> None:
        """
        Borra una lista de suscriptores.

        ADVERTENCIA: Esta operación elimina permanentemente la lista y todos sus suscriptores.
        ⚠️  REQUIERE CONFIRMACIÓN MANUAL ANTES DE USAR

        Args:
            list_id: ID de la lista

        Rate limit: 10 peticiones/minuto
        """
        data = {"list_id": list_id}
        self.client.post("deleteList/", data=data)