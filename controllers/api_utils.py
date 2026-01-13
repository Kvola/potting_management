# -*- coding: utf-8 -*-
"""
Utilitaires pour l'API REST Mobile - Potting Management
Module: potting_management

Ce module fournit:
- Codes d'erreur standardisés
- Validation des entrées robustes
- Rate limiting avancé (sliding window)
- Helpers de réponse API
- Décorateurs d'authentification
- Middleware exception handler
- Circuit breaker pour les services externes
- Correlation ID pour le tracing
- Sanitisation des entrées
"""

import re
import logging
import hashlib
import secrets
import uuid
import html
import time
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
import threading
import json
import traceback
from enum import Enum

from odoo import _, fields
from odoo.http import request, Response
from odoo.exceptions import AccessDenied, AccessError, ValidationError, UserError

_logger = logging.getLogger(__name__)

# Version de l'API
API_VERSION = "1.1.0"

# Constantes de sécurité
MAX_STRING_LENGTH = 10000
MAX_ARRAY_SIZE = 1000
MAX_REQUEST_SIZE = 1024 * 1024  # 1 MB
ALLOWED_CONTENT_TYPES = ['application/json', 'application/x-www-form-urlencoded']


# ==================== CORRELATION ID / TRACING ====================

class RequestContext:
    """Contexte de requête thread-safe pour le tracing"""
    _local = threading.local()
    
    @classmethod
    def get_correlation_id(cls):
        """Obtenir ou créer l'ID de corrélation de la requête"""
        if not hasattr(cls._local, 'correlation_id') or not cls._local.correlation_id:
            # Essayer de récupérer depuis les headers ou générer un nouveau
            if hasattr(request, 'httprequest'):
                cls._local.correlation_id = request.httprequest.headers.get(
                    'X-Correlation-ID',
                    request.httprequest.headers.get('X-Request-ID', str(uuid.uuid4())[:12])
                )
            else:
                cls._local.correlation_id = str(uuid.uuid4())[:12]
        return cls._local.correlation_id
    
    @classmethod
    def set_correlation_id(cls, correlation_id):
        cls._local.correlation_id = correlation_id
    
    @classmethod
    def clear(cls):
        cls._local.correlation_id = None


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
    AUTH_SESSION_INVALID = ("AUTH_008", "Session invalide")
    AUTH_ACCOUNT_LOCKED = ("AUTH_009", "Compte temporairement verrouillé")
    AUTH_RATE_LIMITED = ("AUTH_010", "Trop de tentatives, veuillez réessayer plus tard")
    
    # Validation (2xxx)
    VALIDATION_REQUIRED_FIELD = ("VAL_001", "Champ requis manquant")
    VALIDATION_INVALID_FORMAT = ("VAL_002", "Format invalide")
    VALIDATION_INVALID_VALUE = ("VAL_003", "Valeur invalide")
    VALIDATION_INVALID_DATE = ("VAL_004", "Format de date invalide")
    VALIDATION_INVALID_DATE_RANGE = ("VAL_005", "Plage de dates invalide")
    VALIDATION_INVALID_ID = ("VAL_006", "Identifiant invalide")
    VALIDATION_STRING_TOO_LONG = ("VAL_007", "Chaîne trop longue")
    VALIDATION_ARRAY_TOO_LARGE = ("VAL_008", "Tableau trop grand")
    VALIDATION_INVALID_TYPE = ("VAL_009", "Type de donnée invalide")
    VALIDATION_CONTENT_TYPE = ("VAL_010", "Content-Type non supporté")
    VALIDATION_REQUEST_TOO_LARGE = ("VAL_011", "Requête trop volumineuse")
    
    # Ressources (3xxx)
    RESOURCE_NOT_FOUND = ("RES_001", "Ressource non trouvée")
    RESOURCE_ACCESS_DENIED = ("RES_002", "Accès non autorisé à cette ressource")
    RESOURCE_NO_DATA = ("RES_003", "Aucune donnée trouvée")
    RESOURCE_CONFLICT = ("RES_004", "Conflit avec l'état actuel de la ressource")
    RESOURCE_GONE = ("RES_005", "Ressource supprimée")
    
    # Business Logic (4xxx)
    BUSINESS_REPORT_GENERATION_FAILED = ("BUS_001", "Échec de génération du rapport")
    BUSINESS_NO_TRANSIT_ORDERS = ("BUS_002", "Aucun ordre de transit disponible")
    BUSINESS_INVALID_STATE_TRANSITION = ("BUS_003", "Transition d'état invalide")
    BUSINESS_OPERATION_NOT_ALLOWED = ("BUS_004", "Opération non autorisée dans cet état")
    
    # Serveur (5xxx)
    SERVER_ERROR = ("SRV_001", "Erreur technique, veuillez réessayer")
    SERVER_DATABASE_ERROR = ("SRV_002", "Erreur de base de données")
    SERVER_SERVICE_UNAVAILABLE = ("SRV_003", "Service temporairement indisponible")
    SERVER_TIMEOUT = ("SRV_004", "Délai d'attente dépassé")
    SERVER_MAINTENANCE = ("SRV_005", "Service en maintenance")


# ==================== RATE LIMITING AVANCÉ ====================

class SlidingWindowRateLimiter:
    """Rate limiter avec fenêtre glissante pour plus de précision"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._requests = defaultdict(list)
                    cls._instance._blocked = {}
                    cls._instance._user_requests = defaultdict(list)
        return cls._instance
    
    def _cleanup_old_requests(self, key, window_seconds):
        """Nettoyer les anciennes requêtes"""
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        self._requests[key] = [
            ts for ts in self._requests[key] if ts > cutoff
        ]
    
    def _cleanup_user_requests(self, key, window_seconds):
        """Nettoyer les requêtes utilisateur"""
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        self._user_requests[key] = [
            ts for ts in self._user_requests[key] if ts > cutoff
        ]
    
    def is_rate_limited(self, identifier, max_requests=30, window_seconds=60, block_seconds=300):
        """Vérifier si l'identifiant est limité (par IP)"""
        now = datetime.now()
        key = f"potting_rate:{identifier}"
        
        with self._lock:
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
    
    def is_user_rate_limited(self, user_id, endpoint, max_requests=100, window_seconds=60):
        """Rate limiting par utilisateur et endpoint"""
        now = datetime.now()
        key = f"potting_user:{user_id}:{endpoint}"
        
        with self._lock:
            self._cleanup_user_requests(key, window_seconds)
            
            if len(self._user_requests[key]) >= max_requests:
                return True
            
            self._user_requests[key].append(now)
            return False
    
    def reset(self, identifier):
        """Réinitialiser le compteur"""
        key = f"potting_rate:{identifier}"
        with self._lock:
            if key in self._requests:
                del self._requests[key]
            if key in self._blocked:
                del self._blocked[key]
    
    def get_stats(self, identifier):
        """Obtenir les statistiques de rate limiting"""
        key = f"potting_rate:{identifier}"
        with self._lock:
            return {
                'requests_count': len(self._requests.get(key, [])),
                'is_blocked': key in self._blocked,
                'unblock_at': self._blocked.get(key)
            }


# Garder l'ancien nom pour compatibilité
class RateLimiter(SlidingWindowRateLimiter):
    """Alias pour compatibilité ascendante"""
    pass


rate_limiter = SlidingWindowRateLimiter()


# ==================== VALIDATION ROBUSTE ====================

class InputValidator:
    """Validateur d'entrées robuste avec sanitisation"""
    
    # Patterns de validation
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    PHONE_PATTERN = re.compile(r'^[\d\s\+\-\(\)]{8,20}$')
    ALPHANUMERIC_PATTERN = re.compile(r'^[a-zA-Z0-9_\-]+$')
    SQL_INJECTION_PATTERN = re.compile(r"(--|;|'|\"|\\|\/\*|\*\/|xp_|exec|execute|insert|update|delete|drop|create|alter|truncate)", re.IGNORECASE)
    XSS_PATTERN = re.compile(r'<[^>]*script|javascript:|on\w+\s*=', re.IGNORECASE)
    
    @classmethod
    def sanitize_string(cls, value, max_length=MAX_STRING_LENGTH, escape_html=True):
        """Sanitiser une chaîne de caractères"""
        if not isinstance(value, str):
            return str(value) if value is not None else ''
        
        # Limiter la longueur
        value = value[:max_length]
        
        # Échapper HTML si demandé
        if escape_html:
            value = html.escape(value)
        
        # Supprimer les caractères de contrôle (sauf \n, \r, \t)
        value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)
        
        return value
    
    @classmethod
    def validate_required(cls, value, field_name, strip=True, max_length=MAX_STRING_LENGTH):
        """Valider un champ requis avec sanitisation"""
        if value is None:
            return False, None, {
                'code': APIErrorCodes.VALIDATION_REQUIRED_FIELD[0],
                'message': f"Le champ '{field_name}' est requis",
                'field': field_name
            }
        
        if isinstance(value, str):
            # Vérifier la longueur avant toute opération
            if len(value) > max_length:
                return False, None, {
                    'code': APIErrorCodes.VALIDATION_STRING_TOO_LONG[0],
                    'message': f"Le champ '{field_name}' est trop long (max {max_length} caractères)",
                    'field': field_name
                }
            
            cleaned = value.strip() if strip else value
            if not cleaned:
                return False, None, {
                    'code': APIErrorCodes.VALIDATION_REQUIRED_FIELD[0],
                    'message': f"Le champ '{field_name}' ne peut pas être vide",
                    'field': field_name
                }
            
            # Sanitiser
            cleaned = cls.sanitize_string(cleaned, max_length=max_length)
            return True, cleaned, None
        
        return True, value, None
    
    @classmethod
    def validate_id(cls, value, field_name, required=True):
        """Valider un identifiant numérique"""
        if value is None or value == '':
            if required:
                return False, None, {
                    'code': APIErrorCodes.VALIDATION_REQUIRED_FIELD[0],
                    'message': f"Le champ '{field_name}' est requis",
                    'field': field_name
                }
            return True, None, None
        
        try:
            id_val = int(value)
            if id_val <= 0:
                return False, None, {
                    'code': APIErrorCodes.VALIDATION_INVALID_ID[0],
                    'message': f"L'identifiant '{field_name}' doit être un entier positif",
                    'field': field_name
                }
            return True, id_val, None
        except (ValueError, TypeError):
            return False, None, {
                'code': APIErrorCodes.VALIDATION_INVALID_ID[0],
                'message': f"L'identifiant '{field_name}' doit être un entier valide",
                'field': field_name
            }
    
    @classmethod
    def validate_integer(cls, value, field_name, required=True, min_val=None, max_val=None):
        """Valider un entier avec bornes optionnelles"""
        if value is None or value == '':
            if required:
                return False, None, {
                    'code': APIErrorCodes.VALIDATION_REQUIRED_FIELD[0],
                    'message': f"Le champ '{field_name}' est requis",
                    'field': field_name
                }
            return True, None, None
        
        try:
            int_val = int(value)
            
            if min_val is not None and int_val < min_val:
                return False, None, {
                    'code': APIErrorCodes.VALIDATION_INVALID_VALUE[0],
                    'message': f"Le champ '{field_name}' doit être supérieur ou égal à {min_val}",
                    'field': field_name
                }
            
            if max_val is not None and int_val > max_val:
                return False, None, {
                    'code': APIErrorCodes.VALIDATION_INVALID_VALUE[0],
                    'message': f"Le champ '{field_name}' doit être inférieur ou égal à {max_val}",
                    'field': field_name
                }
            
            return True, int_val, None
        except (ValueError, TypeError):
            return False, None, {
                'code': APIErrorCodes.VALIDATION_INVALID_TYPE[0],
                'message': f"Le champ '{field_name}' doit être un entier",
                'field': field_name
            }
    
    @classmethod
    def validate_float(cls, value, field_name, required=True, min_val=None, max_val=None, precision=2):
        """Valider un nombre décimal"""
        if value is None or value == '':
            if required:
                return False, None, {
                    'code': APIErrorCodes.VALIDATION_REQUIRED_FIELD[0],
                    'message': f"Le champ '{field_name}' est requis",
                    'field': field_name
                }
            return True, None, None
        
        try:
            float_val = round(float(value), precision)
            
            if min_val is not None and float_val < min_val:
                return False, None, {
                    'code': APIErrorCodes.VALIDATION_INVALID_VALUE[0],
                    'message': f"Le champ '{field_name}' doit être supérieur ou égal à {min_val}",
                    'field': field_name
                }
            
            if max_val is not None and float_val > max_val:
                return False, None, {
                    'code': APIErrorCodes.VALIDATION_INVALID_VALUE[0],
                    'message': f"Le champ '{field_name}' doit être inférieur ou égal à {max_val}",
                    'field': field_name
                }
            
            return True, float_val, None
        except (ValueError, TypeError):
            return False, None, {
                'code': APIErrorCodes.VALIDATION_INVALID_TYPE[0],
                'message': f"Le champ '{field_name}' doit être un nombre décimal",
                'field': field_name
            }
    
    @classmethod
    def validate_enum(cls, value, field_name, allowed_values, required=True):
        """Valider une valeur parmi un ensemble autorisé"""
        if value is None or value == '':
            if required:
                return False, None, {
                    'code': APIErrorCodes.VALIDATION_REQUIRED_FIELD[0],
                    'message': f"Le champ '{field_name}' est requis",
                    'field': field_name
                }
            return True, None, None
        
        if value not in allowed_values:
            return False, None, {
                'code': APIErrorCodes.VALIDATION_INVALID_VALUE[0],
                'message': f"Valeur invalide pour '{field_name}'. Valeurs autorisées: {', '.join(map(str, allowed_values))}",
                'field': field_name
            }
        
        return True, value, None
    
    @classmethod
    def validate_email(cls, email, field_name='email', required=True):
        """Valider une adresse email"""
        if not email:
            if required:
                return False, None, {
                    'code': APIErrorCodes.VALIDATION_REQUIRED_FIELD[0],
                    'message': f"Le champ '{field_name}' est requis",
                    'field': field_name
                }
            return True, None, None
        
        email = email.strip().lower()
        if len(email) > 254 or not cls.EMAIL_PATTERN.match(email):
            return False, None, {
                'code': APIErrorCodes.VALIDATION_INVALID_FORMAT[0],
                'message': f"Format d'email invalide pour '{field_name}'",
                'field': field_name
            }
        
        return True, email, None
    
    @classmethod
    def validate_array(cls, value, field_name, max_size=MAX_ARRAY_SIZE, required=True):
        """Valider un tableau"""
        if value is None:
            if required:
                return False, None, {
                    'code': APIErrorCodes.VALIDATION_REQUIRED_FIELD[0],
                    'message': f"Le champ '{field_name}' est requis",
                    'field': field_name
                }
            return True, [], None
        
        if not isinstance(value, list):
            return False, None, {
                'code': APIErrorCodes.VALIDATION_INVALID_TYPE[0],
                'message': f"Le champ '{field_name}' doit être un tableau",
                'field': field_name
            }
        
        if len(value) > max_size:
            return False, None, {
                'code': APIErrorCodes.VALIDATION_ARRAY_TOO_LARGE[0],
                'message': f"Le tableau '{field_name}' est trop grand (max {max_size} éléments)",
                'field': field_name
            }
        
        return True, value, None
    
    @classmethod
    def validate_date(cls, date_str, field_name, required=True, min_date=None, max_date=None):
        """Valider et parser une date (format: YYYY-MM-DD)"""
        if not date_str:
            if required:
                return False, None, {
                    'code': APIErrorCodes.VALIDATION_REQUIRED_FIELD[0],
                    'message': f"Le champ '{field_name}' est requis",
                    'field': field_name
                }
            return True, None, None
        
        # Sanitiser l'entrée
        if isinstance(date_str, str):
            date_str = date_str.strip()[:20]  # Longueur max raisonnable pour une date
        
        try:
            parsed = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            if min_date and parsed < min_date:
                return False, None, {
                    'code': APIErrorCodes.VALIDATION_INVALID_VALUE[0],
                    'message': f"La date '{field_name}' doit être après {min_date}",
                    'field': field_name
                }
            
            if max_date and parsed > max_date:
                return False, None, {
                    'code': APIErrorCodes.VALIDATION_INVALID_VALUE[0],
                    'message': f"La date '{field_name}' doit être avant {max_date}",
                    'field': field_name
                }
            
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
    
    @classmethod
    def check_sql_injection(cls, value):
        """Vérifier les tentatives d'injection SQL"""
        if isinstance(value, str) and cls.SQL_INJECTION_PATTERN.search(value):
            _logger.warning(f"[SECURITY] Tentative d'injection SQL détectée: {value[:100]}")
            return True
        return False
    
    @classmethod
    def check_xss(cls, value):
        """Vérifier les tentatives XSS"""
        if isinstance(value, str) and cls.XSS_PATTERN.search(value):
            _logger.warning(f"[SECURITY] Tentative XSS détectée: {value[:100]}")
            return True
        return False
    
    @classmethod
    def validate_pagination(cls, page, limit, max_limit=100, default_limit=20):
        """Valider et normaliser les paramètres de pagination"""
        try:
            page = max(1, int(page)) if page else 1
        except (ValueError, TypeError):
            page = 1
        
        try:
            limit = min(max_limit, max(1, int(limit))) if limit else default_limit
        except (ValueError, TypeError):
            limit = default_limit
        
        offset = (page - 1) * limit
        
        return page, limit, offset


# ==================== HELPERS RÉPONSE API ====================

def _add_security_headers(response):
    """Ajouter les headers de sécurité à une réponse"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    
    # Ajouter correlation ID
    correlation_id = RequestContext.get_correlation_id()
    if correlation_id:
        response.headers['X-Correlation-ID'] = correlation_id
    
    return response


def api_response(data=None, message=None, status=200, meta=None, headers=None):
    """Générer une réponse API standardisée (succès)"""
    correlation_id = RequestContext.get_correlation_id()
    
    response_data = {
        'success': True,
        'api_version': API_VERSION,
        'timestamp': datetime.now().isoformat(),
        'correlation_id': correlation_id,
    }
    
    if message:
        response_data['message'] = message
    
    if data is not None:
        response_data['data'] = data
    
    if meta:
        response_data['meta'] = meta
    
    response = Response(
        json.dumps(response_data, default=str),
        content_type='application/json',
        status=status
    )
    
    response = _add_security_headers(response)
    
    if headers:
        for key, value in headers.items():
            response.headers[key] = value
    
    return response


def api_error(error_code_tuple, message=None, status=400, details=None, log_error=True):
    """Générer une réponse API standardisée (erreur)"""
    code, default_message = error_code_tuple
    correlation_id = RequestContext.get_correlation_id()
    
    response_data = {
        'success': False,
        'api_version': API_VERSION,
        'timestamp': datetime.now().isoformat(),
        'correlation_id': correlation_id,
        'error': {
            'code': code,
            'message': message or default_message
        }
    }
    
    if details:
        response_data['error']['details'] = details
    
    if log_error:
        _logger.warning(f"[POTTING API ERROR] [{correlation_id}] {code}: {message or default_message}")
    
    response = Response(
        json.dumps(response_data, default=str),
        content_type='application/json',
        status=status
    )
    
    return _add_security_headers(response)


def api_validation_error(errors, log_error=True):
    """Générer une erreur de validation"""
    correlation_id = RequestContext.get_correlation_id()
    
    error_list = errors if isinstance(errors, list) else [errors]
    
    if log_error:
        _logger.info(f"[POTTING API VALIDATION] [{correlation_id}] {len(error_list)} erreur(s)")
    
    response = Response(
        json.dumps({
            'success': False,
            'api_version': API_VERSION,
            'timestamp': datetime.now().isoformat(),
            'correlation_id': correlation_id,
            'error': {
                'code': 'VALIDATION_ERROR',
                'message': 'Erreurs de validation',
                'details': error_list
            }
        }, default=str),
        content_type='application/json',
        status=422
    )
    
    return _add_security_headers(response)


# ==================== UTILITAIRES ====================

def get_client_ip():
    """Obtenir l'adresse IP du client de manière sécurisée"""
    try:
        # Vérifier X-Forwarded-For (attention: peut être falsifié)
        xff = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR')
        if xff:
            # Prendre la première IP (client original)
            ip = xff.split(',')[0].strip()
            # Validation basique de l'IP
            if re.match(r'^[\d\.:a-fA-F]+$', ip):
                return ip
        
        # X-Real-IP (proxy nginx)
        xri = request.httprequest.environ.get('HTTP_X_REAL_IP')
        if xri and re.match(r'^[\d\.:a-fA-F]+$', xri):
            return xri
        
        return request.httprequest.environ.get('REMOTE_ADDR', 'unknown')
    except Exception:
        return 'unknown'


def log_api_call(endpoint, user_id=None, success=True, details=None, duration_ms=None):
    """Logger un appel API avec contexte enrichi"""
    correlation_id = RequestContext.get_correlation_id()
    ip = get_client_ip()
    status = "SUCCESS" if success else "FAILED"
    user_info = f"user_id={user_id}" if user_id else "anonymous"
    
    log_msg = f"[POTTING API] [{correlation_id}] {endpoint} | {status} | {user_info} | IP: {ip}"
    if duration_ms is not None:
        log_msg += f" | {duration_ms:.0f}ms"
    if details:
        log_msg += f" | {details}"
    
    if success:
        _logger.info(log_msg)
    else:
        _logger.warning(log_msg)


# ==================== CIRCUIT BREAKER ====================

class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Circuit breaker pour protéger contre les pannes en cascade.
    
    Usage:
        breaker = CircuitBreaker('database', failure_threshold=5)
        if breaker.allow_request():
            try:
                result = do_database_operation()
                breaker.record_success()
            except Exception:
                breaker.record_failure()
    """
    
    _instances = {}
    _lock = threading.Lock()
    
    def __new__(cls, name, failure_threshold=5, recovery_timeout=30, half_open_max=3):
        with cls._lock:
            if name not in cls._instances:
                instance = super().__new__(cls)
                instance._name = name
                instance._failure_threshold = failure_threshold
                instance._recovery_timeout = recovery_timeout
                instance._half_open_max = half_open_max
                instance._state = CircuitBreakerState.CLOSED
                instance._failure_count = 0
                instance._success_count = 0
                instance._last_failure_time = None
                instance._half_open_attempts = 0
                instance._instance_lock = threading.Lock()
                cls._instances[name] = instance
            return cls._instances[name]
    
    @property
    def state(self):
        return self._state
    
    @property
    def name(self):
        return self._name
    
    def allow_request(self):
        """Vérifier si une requête est autorisée"""
        with self._instance_lock:
            if self._state == CircuitBreakerState.CLOSED:
                return True
            
            if self._state == CircuitBreakerState.OPEN:
                # Vérifier si le timeout est passé
                if self._last_failure_time:
                    elapsed = (datetime.now() - self._last_failure_time).total_seconds()
                    if elapsed >= self._recovery_timeout:
                        self._state = CircuitBreakerState.HALF_OPEN
                        self._half_open_attempts = 0
                        _logger.info(f"[CIRCUIT BREAKER] {self._name}: OPEN -> HALF_OPEN")
                        return True
                return False
            
            # HALF_OPEN: autoriser quelques tentatives
            if self._half_open_attempts < self._half_open_max:
                self._half_open_attempts += 1
                return True
            return False
    
    def record_success(self):
        """Enregistrer un succès"""
        with self._instance_lock:
            if self._state == CircuitBreakerState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= 2:  # 2 succès pour fermer
                    self._state = CircuitBreakerState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    _logger.info(f"[CIRCUIT BREAKER] {self._name}: HALF_OPEN -> CLOSED")
            elif self._state == CircuitBreakerState.CLOSED:
                # Réinitialiser le compteur d'échecs en cas de succès
                self._failure_count = max(0, self._failure_count - 1)
    
    def record_failure(self):
        """Enregistrer un échec"""
        with self._instance_lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now()
            
            if self._state == CircuitBreakerState.HALF_OPEN:
                self._state = CircuitBreakerState.OPEN
                _logger.warning(f"[CIRCUIT BREAKER] {self._name}: HALF_OPEN -> OPEN")
            elif self._state == CircuitBreakerState.CLOSED:
                if self._failure_count >= self._failure_threshold:
                    self._state = CircuitBreakerState.OPEN
                    _logger.warning(f"[CIRCUIT BREAKER] {self._name}: CLOSED -> OPEN (failures={self._failure_count})")
    
    def reset(self):
        """Réinitialiser le circuit breaker"""
        with self._instance_lock:
            self._state = CircuitBreakerState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            self._half_open_attempts = 0
    
    def get_status(self):
        """Obtenir le statut du circuit breaker"""
        return {
            'name': self._name,
            'state': self._state.value,
            'failure_count': self._failure_count,
            'last_failure': self._last_failure_time.isoformat() if self._last_failure_time else None
        }


# Circuit breakers globaux
db_circuit_breaker = CircuitBreaker('database', failure_threshold=5, recovery_timeout=30)
report_circuit_breaker = CircuitBreaker('report_generation', failure_threshold=3, recovery_timeout=60)


# ==================== DÉCORATEURS ====================

def api_exception_handler(func):
    """
    Décorateur pour capturer toutes les exceptions et retourner une réponse standardisée.
    Doit être le décorateur le plus externe.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        correlation_id = RequestContext.get_correlation_id()
        
        try:
            # Initialiser le contexte de requête
            RequestContext.set_correlation_id(correlation_id)
            
            result = func(*args, **kwargs)
            
            # Log durée pour monitoring
            duration_ms = (time.time() - start_time) * 1000
            if duration_ms > 1000:  # Log si > 1 seconde
                _logger.info(f"[POTTING API SLOW] [{correlation_id}] {func.__name__} took {duration_ms:.0f}ms")
            
            return result
            
        except AccessDenied as e:
            _logger.warning(f"[POTTING API] [{correlation_id}] AccessDenied: {e}")
            return api_error(
                APIErrorCodes.AUTH_INSUFFICIENT_RIGHTS,
                str(e) if str(e) else None,
                status=403
            )
        
        except AccessError as e:
            _logger.warning(f"[POTTING API] [{correlation_id}] AccessError: {e}")
            return api_error(
                APIErrorCodes.RESOURCE_ACCESS_DENIED,
                str(e) if str(e) else None,
                status=403
            )
        
        except ValidationError as e:
            _logger.info(f"[POTTING API] [{correlation_id}] ValidationError: {e}")
            return api_error(
                APIErrorCodes.VALIDATION_INVALID_VALUE,
                str(e),
                status=400
            )
        
        except UserError as e:
            _logger.info(f"[POTTING API] [{correlation_id}] UserError: {e}")
            return api_error(
                APIErrorCodes.BUSINESS_OPERATION_NOT_ALLOWED,
                str(e),
                status=400
            )
        
        except json.JSONDecodeError as e:
            _logger.warning(f"[POTTING API] [{correlation_id}] JSONDecodeError: {e}")
            return api_error(
                APIErrorCodes.VALIDATION_INVALID_FORMAT,
                "Format JSON invalide",
                status=400
            )
        
        except Exception as e:
            # Log l'exception complète pour le debugging
            _logger.exception(f"[POTTING API ERROR] [{correlation_id}] Unhandled exception in {func.__name__}: {e}")
            
            # En production, ne pas exposer les détails de l'erreur
            return api_error(
                APIErrorCodes.SERVER_ERROR,
                status=500
            )
        
        finally:
            # Nettoyer le contexte
            RequestContext.clear()
    
    return wrapper


def rate_limit(max_requests=30, window_seconds=60):
    """Décorateur de rate limiting par IP"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            ip = get_client_ip()
            is_limited, remaining = rate_limiter.is_rate_limited(
                ip, max_requests, window_seconds
            )
            
            if is_limited:
                log_api_call(func.__name__, success=False, details=f"Rate limited, retry in {remaining}s")
                response = api_error(
                    APIErrorCodes.AUTH_RATE_LIMITED,
                    f"Trop de requêtes. Réessayez dans {remaining} secondes.",
                    status=429
                )
                response.headers['Retry-After'] = str(remaining)
                return response
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def rate_limit_user(max_requests=100, window_seconds=60):
    """Décorateur de rate limiting par utilisateur authentifié"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Récupérer l'utilisateur si disponible
            user_id = getattr(request, 'ceo_user', None)
            if user_id:
                user_id = user_id.id if hasattr(user_id, 'id') else user_id
            else:
                user_id = get_client_ip()  # Fallback sur IP
            
            if rate_limiter.is_user_rate_limited(user_id, func.__name__, max_requests, window_seconds):
                return api_error(
                    APIErrorCodes.AUTH_RATE_LIMITED,
                    "Limite de requêtes atteinte pour cet utilisateur.",
                    status=429
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_auth(func):
    """
    Décorateur unifié pour l'authentification API.
    Vérifie le token Bearer et stocke l'utilisateur dans request.api_user.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        correlation_id = RequestContext.get_correlation_id()
        
        # Récupérer le token depuis les headers
        auth_header = request.httprequest.headers.get('Authorization', '')
        
        if not auth_header:
            log_api_call(func.__name__, success=False, details="Missing auth header")
            return api_error(
                APIErrorCodes.AUTH_TOKEN_MISSING,
                status=401
            )
        
        # Format attendu: "Bearer <token>"
        if not auth_header.startswith('Bearer '):
            log_api_call(func.__name__, success=False, details="Invalid auth format")
            return api_error(
                APIErrorCodes.AUTH_TOKEN_INVALID,
                "Format de token invalide. Utilisez 'Bearer <token>'",
                status=401
            )
        
        token = auth_header[7:]  # Retirer "Bearer "
        
        # Validation basique du token
        if not token or len(token) < 32 or len(token) > 256:
            return api_error(
                APIErrorCodes.AUTH_TOKEN_INVALID,
                status=401
            )
        
        # Vérifier le token
        try:
            user = self._verify_api_token(token)
        except Exception as e:
            _logger.error(f"[POTTING API] [{correlation_id}] Token verification error: {e}")
            return api_error(
                APIErrorCodes.SERVER_ERROR,
                status=500
            )
        
        if not user:
            log_api_call(func.__name__, success=False, details="Invalid token")
            return api_error(
                APIErrorCodes.AUTH_TOKEN_INVALID,
                status=401
            )
        
        # Vérifier que l'utilisateur est toujours actif
        if not user.active:
            log_api_call(func.__name__, user_id=user.id, success=False, details="User inactive")
            return api_error(
                APIErrorCodes.AUTH_USER_INACTIVE,
                status=401
            )
        
        # Stocker l'utilisateur dans le contexte de la requête
        request.api_user = user
        request.ceo_user = user  # Compatibilité ascendante
        
        return func(self, *args, **kwargs)
    return wrapper


# Alias pour compatibilité
require_ceo_auth = require_auth


def with_circuit_breaker(breaker):
    """Décorateur pour utiliser un circuit breaker"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not breaker.allow_request():
                _logger.warning(f"[CIRCUIT BREAKER] {breaker.name} is OPEN, rejecting request")
                return api_error(
                    APIErrorCodes.SERVER_SERVICE_UNAVAILABLE,
                    "Service temporairement indisponible. Réessayez plus tard.",
                    status=503
                )
            
            try:
                result = func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure()
                raise
        return wrapper
    return decorator


def format_currency(amount, currency_symbol='FCFA'):
    """Formater un montant monétaire"""
    if amount is None:
        return "0 " + currency_symbol
    return "{:,.0f} {}".format(amount, currency_symbol).replace(',', ' ')
