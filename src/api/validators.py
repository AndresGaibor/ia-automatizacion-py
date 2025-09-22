"""
Validadores para la API de Acumbamail
"""
import re
from datetime import datetime
from typing import Tuple


class DateValidator:
    """Validador para fechas en formato YYYY-MM-DD"""
    
    DATE_PATTERN = r'^\d{4}-\d{2}-\d{2}$'
    DATE_FORMAT = '%Y-%m-%d'
    
    @classmethod
    def validate_date_format(cls, date_str: str, field_name: str = "date") -> None:
        """
        Validar que una fecha tenga el formato correcto YYYY-MM-DD
        
        Args:
            date_str: Fecha a validar
            field_name: Nombre del campo para mensajes de error
            
        Raises:
            ValueError: Si el formato es incorrecto o la fecha es inválida
        """
        if not re.match(cls.DATE_PATTERN, date_str):
            raise ValueError(f"{field_name} debe tener formato YYYY-MM-DD, recibido: {date_str}")
        
        # Validar que sea una fecha válida
        try:
            datetime.strptime(date_str, cls.DATE_FORMAT)
        except ValueError as e:
            raise ValueError(f"Fecha inválida en {field_name}: {e}")
    
    @classmethod
    def validate_date_range(cls, start_date: str, end_date: str) -> Tuple[datetime, datetime]:
        """
        Validar un rango de fechas
        
        Args:
            start_date: Fecha de inicio (YYYY-MM-DD)
            end_date: Fecha de fin (YYYY-MM-DD)
            
        Returns:
            Tuple con los objetos datetime validados
            
        Raises:
            ValueError: Si alguna fecha es inválida o el rango es incorrecto
        """
        # Validar formatos
        cls.validate_date_format(start_date, "start_date")
        cls.validate_date_format(end_date, "end_date")
        
        # Convertir a datetime
        start_dt = datetime.strptime(start_date, cls.DATE_FORMAT)
        end_dt = datetime.strptime(end_date, cls.DATE_FORMAT)
        
        # Validar que start_date sea anterior o igual a end_date
        if start_dt > end_dt:
            raise ValueError(f"start_date ({start_date}) debe ser anterior o igual a end_date ({end_date})")
        
        return start_dt, end_dt


class CampaignValidator:
    """Validadores específicos para campañas"""
    
    @staticmethod
    def validate_campaign_id(campaign_id: int) -> None:
        """
        Validar que el ID de campaña sea válido
        
        Args:
            campaign_id: ID de la campaña
            
        Raises:
            ValueError: Si el ID no es válido
        """
        if not isinstance(campaign_id, int):
            raise ValueError(f"campaign_id debe ser un entero, recibido: {type(campaign_id).__name__}")
        
        if campaign_id <= 0:
            raise ValueError(f"campaign_id debe ser positivo, recibido: {campaign_id}")


class EmailValidator:
    """Validadores para emails"""
    
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    @classmethod
    def validate_email(cls, email: str) -> None:
        """
        Validar formato de email
        
        Args:
            email: Email a validar
            
        Raises:
            ValueError: Si el email no es válido
        """
        if not isinstance(email, str):
            raise ValueError(f"Email debe ser string, recibido: {type(email).__name__}")
        
        if not email.strip():
            raise ValueError("Email no puede estar vacío")
        
        if not re.match(cls.EMAIL_PATTERN, email):
            raise ValueError(f"Formato de email inválido: {email}")