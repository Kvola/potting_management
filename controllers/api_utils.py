# -*- coding: utf-8 -*-
"""
Utilitaires pour l'API REST Mobile - Potting Management
Module: potting_management

Ce module fournit:
- Codes d'erreur standardisés
- Validation des entrées
- Rate limiting
- Helpers de réponse API
- Décorateurs d'authentification
"""

import re
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
import threading
import json

from odoo import _, fields
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

# Version de l'API
API_VERSION = "1.0.0"


# ==================== CODES D'ERREUR STANDARDISÉS ====================

class APIErrorCodes:
    """Codes d'erreur standardisés pour l'API Potting"""
    
    # Authentification (1xxx)
    AUTH_TOKEN_MISSING = ("AUTH_001", "Token d'authentification manquant")
    AUTH_TOKEN_INVALID = ("AUTH_002", "Token invalide ou expiré")
    AUTH_TOKEN_EXPIRED = ("AUTH_003", "Token expiré, veuillez vous reconnecter")
    AUTH_USER_INACTIVE = ("AUTH_004", "Votre compte utilisateur n'est pas actif")
    AUTH_PASSWORD_INCORRECT = ("AUTH_005", "Mot de passe incorrect")
    AUTH_USER_NOT_FOUND = ("AUTH_006", "Utilisateur non trouvé")
    AUTH_INSUFFICIENT_RIGHTS = ("AUTH_007", "Droits insuffisants pour cette opération")
    AUTH_RATE_LIMITED = ("AUTH_010", "Trop de tentatives, veuillez réessayer plus tard")
    
    # Validation (2xxx)
    VALIDATION_REQUIRED_FIELD = ("VAL_001", "Champ requis manquant")
    VALIDATION_INVALID_FORMAT = ("VAL_002", "Format invalide")
    VALIDATION_INVALID_VALUE = ("VAL_003", "Valeur invalide")
    VALIDATION_INVALID_DATE = ("VAL_004", "Format de date invalide")
    VALIDATION_INVALID_DATE_RANGE = ("VAL_005", "Plage de dates invalide")
    
    # Ressources (3xxx)
    RESOURCE_NOT_FOUND = ("RES_001", "Ressource non trouvée")
    RESOURCE_ACCESS_DENIED = ("RES_002", "Accès non autorisé à cette ressource")
    RESOURCE_NO_DATA = ("RES_003", "Aucune donnée trouvée")
    
    # Business Logic (4xxx)
    BUSINESS_REPORT_GENERATION_FAILED = ("BUS_001", "Échec de génération du rapport")
    BUSINESS_NO_TRANSIT_ORDERS = ("BUS_002", "Aucun ordre de transit disponible")
    
    # Serveur (5xxx)
    SERVER_ERROR = ("SRV_001", "Erreur technique, veuillez réessayer")
    SERVER_DATABASE_ERROR = ("SRV_002", "Erreur de base de données")


# ==================== RATE LIMITING ====================

class RateLimiter:
    """Rate limiter simple en mémoire"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._requests = defaultdict(list)
                    cls._instance._blocked = {}
        return cls._instance
    
    def _cleanup_old_requests(self, key, window_seconds):
        """Nettoyer les anciennes requêtes"""
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        self._requests[key] = [
            ts for ts in self._requests[key] if ts > cutoff
        ]
    
    def is_rate_limited(self, identifier, max_requests=30, window_seconds=60, block_seconds=300):
        """Vérifier si l'identifiant est limité"""
        now = datetime.now()
        key = f"potting_rate:{identifier}"
        
        if key in self._blocked:
            unblock_time = self._blocked[key]
            if now < unblock_time:
                remaining = (unblock_time - now).total_seconds()
                return True, int(remaining)
            else:
                del self._blocked[key]
        
        self._cleanup_old_requests(key, window_seconds)
        
        if len(self._requests[key]) >= max_requests:
            self._blocked[key] = now + timedelta(seconds=block_seconds)
            return True, block_seconds
        
        self._requests[key].append(now)
        return False, 0
    
    def reset(self, identifier):
        """Réinitialiser le compteur"""
        key = f"potting_rate:{identifier}"
        if key in self._requests:
            del self._requests[key]
        if key in self._blocked:
            del self._blocked[key]


rate_limiter = RateLimiter()


# ==================== VALIDATION ====================

class InputValidator:
    """Validateur d'entrées"""
    
    @classmethod
    def validate_required(cls, value, field_name, strip=True):
        """Valider un champ requis"""
        if value is None:
            return False, None, {
                'code': APIErrorCodes.VALIDATION_REQUIRED_FIELD[0],
                'message': f"Le champ '{field_name}' est requis",
                'field': field_name
            }
        
        if isinstance(value, str):
            cleaned = value.strip() if strip else value
            if not cleaned:
                return False, None, {
                    'code': APIErrorCodes.VALIDATION_REQUIRED_FIELD[0],
                    'message': f"Le champ '{field_name}' ne peut pas être vide",
                    'field': field_name
                }
            return True, cleaned, None
        
        return True, value, None
    
    @classmethod
    def validate_date(cls, date_str, field_name, required=True):
        """Valider et parser une date (format: YYYY-MM-DD)"""
        if not date_str:
            if required:
                return False, None, {
                    'code': APIErrorCodes.VALIDATION_REQUIRED_FIELD[0],
                    'message': f"Le champ '{field_name}' est requis",
                    'field': field_name
                }
            return True, None, None
        
        try:
            parsed = datetime.strptime(date_str, '%Y-%m-%d').date()
            return True, parsed, None
        except ValueError:
            return False, None, {
                'code': APIErrorCodes.VALIDATION_INVALID_DATE[0],
                'message': f"Format de date invalide pour '{field_name}'. Utilisez YYYY-MM-DD",
                'field': field_name
            }
    
    @classmethod
    def validate_date_range(cls, date_from, date_to):
        """Valider une plage de dates"""
        if date_from and date_to and date_from > date_to:
            return False, {
                'code': APIErrorCodes.VALIDATION_INVALID_DATE_RANGE[0],
                'message': "La date de début doit être antérieure à la date de fin"
            }
        return True, None


# ==================== HELPERS RÉPONSE API ====================

def api_response(data=None, message=None, status=200, meta=None):
    """Générer une réponse API standardisée (succès)"""
    response_data = {
        'success': True,
        'api_version': API_VERSION,
        'timestamp': datetime.now().isoformat(),
    }
    
    if message:
        response_data['message'] = message
    
    if data is not None:
        response_data['data'] = data
    
    if meta:
        response_data['meta'] = meta
    
    return Response(
        json.dumps(response_data, default=str),
        content_type='application/json',
        status=status
    )


def api_error(error_code_tuple, message=None, status=400, details=None):
    """Générer une réponse API standardisée (erreur)"""
    code, default_message = error_code_tuple
    
    response_data = {
        'success': False,
        'api_version': API_VERSION,
        'timestamp': datetime.now().isoformat(),
        'error': {
            'code': code,
            'message': message or default_message
        }
    }
    
    if details:
        response_data['error']['details'] = details
    
    return Response(
        json.dumps(response_data, default=str),
        content_type='application/json',
        status=status
    )


def api_validation_error(errors):
    """Générer une erreur de validation"""
    return Response(
        json.dumps({
            'success': False,
            'api_version': API_VERSION,
            'timestamp': datetime.now().isoformat(),
            'error': {
                'code': 'VALIDATION_ERROR',
                'message': 'Erreurs de validation',
                'details': errors if isinstance(errors, list) else [errors]
            }
        }, default=str),
        content_type='application/json',
        status=422
    )


# ==================== UTILITAIRES ====================

def get_client_ip():
    """Obtenir l'adresse IP du client"""
    if request.httprequest.environ.get('HTTP_X_FORWARDED_FOR'):
        return request.httprequest.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
    return request.httprequest.environ.get('REMOTE_ADDR', 'unknown')


def log_api_call(endpoint, user_id=None, success=True, details=None):
    """Logger un appel API"""
    ip = get_client_ip()
    status = "SUCCESS" if success else "FAILED"
    user_info = f"user_id={user_id}" if user_id else "anonymous"
    
    log_msg = f"[POTTING API] {endpoint} | {status} | {user_info} | IP: {ip}"
    if details:
        log_msg += f" | {details}"
    
    if success:
        _logger.info(log_msg)
    else:
        _logger.warning(log_msg)


# ==================== DÉCORATEURS ====================

def rate_limit(max_requests=30, window_seconds=60):
    """Décorateur de rate limiting"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            ip = get_client_ip()
            is_limited, remaining = rate_limiter.is_rate_limited(
                ip, max_requests, window_seconds
            )
            
            if is_limited:
                return api_error(
                    APIErrorCodes.AUTH_RATE_LIMITED,
                    f"Trop de requêtes. Réessayez dans {remaining} secondes.",
                    status=429
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_ceo_auth(func):
    """
    Décorateur pour authentification PDG.
    Vérifie le token API et les droits d'accès.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # Récupérer le token depuis les headers
        auth_header = request.httprequest.headers.get('Authorization', '')
        
        if not auth_header:
            return api_error(
                APIErrorCodes.AUTH_TOKEN_MISSING,
                status=401
            )
        
        # Format attendu: "Bearer <token>"
        if not auth_header.startswith('Bearer '):
            return api_error(
                APIErrorCodes.AUTH_TOKEN_INVALID,
                "Format de token invalide. Utilisez 'Bearer <token>'",
                status=401
            )
        
        token = auth_header[7:]  # Retirer "Bearer "
        
        # Vérifier le token
        user = self._verify_api_token(token)
        if not user:
            return api_error(
                APIErrorCodes.AUTH_TOKEN_INVALID,
                status=401
            )
        
        # Stocker l'utilisateur dans le contexte de la requête
        request.ceo_user = user
        
        return func(self, *args, **kwargs)
    return wrapper


def format_currency(amount, currency_symbol='FCFA'):
    """Formater un montant monétaire"""
    if amount is None:
        return "0 " + currency_symbol
    return "{:,.0f} {}".format(amount, currency_symbol).replace(',', ' ')
