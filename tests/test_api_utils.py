# -*- coding: utf-8 -*-
"""
Tests unitaires pour les utilitaires de l'API REST Potting
Module: potting_management
"""

from datetime import datetime, date, timedelta
from unittest.mock import MagicMock, patch
import json

from odoo.tests.common import TransactionCase


class TestInputValidator(TransactionCase):
    """Tests pour la classe InputValidator"""

    def setUp(self):
        super().setUp()
        from ..controllers.api_utils import InputValidator, APIErrorCodes
        self.validator = InputValidator
        self.error_codes = APIErrorCodes

    # ========== Tests validate_required ==========

    def test_validate_required_none_value(self):
        """Test champ requis avec valeur None"""
        valid, value, error = self.validator.validate_required(None, 'test_field')
        self.assertFalse(valid)
        self.assertIsNone(value)
        self.assertEqual(error['code'], self.error_codes.VALIDATION_REQUIRED_FIELD[0])
        self.assertIn('test_field', error['message'])

    def test_validate_required_empty_string(self):
        """Test champ requis avec chaîne vide"""
        valid, value, error = self.validator.validate_required('   ', 'test_field')
        self.assertFalse(valid)
        self.assertIsNone(value)
        self.assertEqual(error['code'], self.error_codes.VALIDATION_REQUIRED_FIELD[0])

    def test_validate_required_valid_string(self):
        """Test champ requis avec valeur valide"""
        valid, value, error = self.validator.validate_required('  test value  ', 'test_field')
        self.assertTrue(valid)
        self.assertEqual(value, 'test value')  # Doit être strippé
        self.assertIsNone(error)

    def test_validate_required_string_too_long(self):
        """Test champ requis avec chaîne trop longue"""
        long_string = 'x' * 15000
        valid, value, error = self.validator.validate_required(long_string, 'test_field')
        self.assertFalse(valid)
        self.assertEqual(error['code'], self.error_codes.VALIDATION_STRING_TOO_LONG[0])

    def test_validate_required_integer_value(self):
        """Test champ requis avec entier"""
        valid, value, error = self.validator.validate_required(42, 'test_field')
        self.assertTrue(valid)
        self.assertEqual(value, 42)
        self.assertIsNone(error)

    # ========== Tests validate_id ==========

    def test_validate_id_valid(self):
        """Test ID valide"""
        valid, value, error = self.validator.validate_id('123', 'record_id')
        self.assertTrue(valid)
        self.assertEqual(value, 123)
        self.assertIsNone(error)

    def test_validate_id_zero(self):
        """Test ID zéro (invalide)"""
        valid, value, error = self.validator.validate_id('0', 'record_id')
        self.assertFalse(valid)
        self.assertEqual(error['code'], self.error_codes.VALIDATION_INVALID_ID[0])

    def test_validate_id_negative(self):
        """Test ID négatif (invalide)"""
        valid, value, error = self.validator.validate_id('-5', 'record_id')
        self.assertFalse(valid)
        self.assertEqual(error['code'], self.error_codes.VALIDATION_INVALID_ID[0])

    def test_validate_id_non_numeric(self):
        """Test ID non numérique"""
        valid, value, error = self.validator.validate_id('abc', 'record_id')
        self.assertFalse(valid)
        self.assertEqual(error['code'], self.error_codes.VALIDATION_INVALID_ID[0])

    def test_validate_id_optional_empty(self):
        """Test ID optionnel vide"""
        valid, value, error = self.validator.validate_id('', 'record_id', required=False)
        self.assertTrue(valid)
        self.assertIsNone(value)
        self.assertIsNone(error)

    # ========== Tests validate_integer ==========

    def test_validate_integer_valid(self):
        """Test entier valide"""
        valid, value, error = self.validator.validate_integer('42', 'quantity')
        self.assertTrue(valid)
        self.assertEqual(value, 42)

    def test_validate_integer_with_min(self):
        """Test entier avec valeur minimum"""
        valid, value, error = self.validator.validate_integer('5', 'quantity', min_val=10)
        self.assertFalse(valid)
        self.assertEqual(error['code'], self.error_codes.VALIDATION_INVALID_VALUE[0])

    def test_validate_integer_with_max(self):
        """Test entier avec valeur maximum"""
        valid, value, error = self.validator.validate_integer('150', 'quantity', max_val=100)
        self.assertFalse(valid)
        self.assertEqual(error['code'], self.error_codes.VALIDATION_INVALID_VALUE[0])

    def test_validate_integer_in_range(self):
        """Test entier dans la plage"""
        valid, value, error = self.validator.validate_integer('50', 'quantity', min_val=10, max_val=100)
        self.assertTrue(valid)
        self.assertEqual(value, 50)

    # ========== Tests validate_float ==========

    def test_validate_float_valid(self):
        """Test nombre décimal valide"""
        valid, value, error = self.validator.validate_float('42.567', 'amount')
        self.assertTrue(valid)
        self.assertEqual(value, 42.57)  # Arrondi à 2 décimales par défaut

    def test_validate_float_with_precision(self):
        """Test nombre décimal avec précision"""
        valid, value, error = self.validator.validate_float('42.5678', 'amount', precision=3)
        self.assertTrue(valid)
        self.assertEqual(value, 42.568)

    # ========== Tests validate_enum ==========

    def test_validate_enum_valid(self):
        """Test valeur enum valide"""
        valid, value, error = self.validator.validate_enum(
            'draft', 'state', ['draft', 'confirmed', 'done']
        )
        self.assertTrue(valid)
        self.assertEqual(value, 'draft')

    def test_validate_enum_invalid(self):
        """Test valeur enum invalide"""
        valid, value, error = self.validator.validate_enum(
            'invalid_state', 'state', ['draft', 'confirmed', 'done']
        )
        self.assertFalse(valid)
        self.assertEqual(error['code'], self.error_codes.VALIDATION_INVALID_VALUE[0])
        self.assertIn('draft', error['message'])

    def test_validate_enum_optional_empty(self):
        """Test enum optionnel vide"""
        valid, value, error = self.validator.validate_enum(
            '', 'state', ['draft', 'confirmed'], required=False
        )
        self.assertTrue(valid)
        self.assertIsNone(value)

    # ========== Tests validate_email ==========

    def test_validate_email_valid(self):
        """Test email valide"""
        valid, value, error = self.validator.validate_email('Test@Example.COM', 'email')
        self.assertTrue(valid)
        self.assertEqual(value, 'test@example.com')  # Doit être en minuscules

    def test_validate_email_invalid(self):
        """Test email invalide"""
        valid, value, error = self.validator.validate_email('not-an-email', 'email')
        self.assertFalse(valid)
        self.assertEqual(error['code'], self.error_codes.VALIDATION_INVALID_FORMAT[0])

    def test_validate_email_too_long(self):
        """Test email trop long"""
        long_email = 'a' * 250 + '@test.com'
        valid, value, error = self.validator.validate_email(long_email, 'email')
        self.assertFalse(valid)

    # ========== Tests validate_array ==========

    def test_validate_array_valid(self):
        """Test tableau valide"""
        valid, value, error = self.validator.validate_array([1, 2, 3], 'items')
        self.assertTrue(valid)
        self.assertEqual(value, [1, 2, 3])

    def test_validate_array_not_list(self):
        """Test valeur qui n'est pas un tableau"""
        valid, value, error = self.validator.validate_array('not a list', 'items')
        self.assertFalse(valid)
        self.assertEqual(error['code'], self.error_codes.VALIDATION_INVALID_TYPE[0])

    def test_validate_array_too_large(self):
        """Test tableau trop grand"""
        large_array = list(range(2000))
        valid, value, error = self.validator.validate_array(large_array, 'items', max_size=100)
        self.assertFalse(valid)
        self.assertEqual(error['code'], self.error_codes.VALIDATION_ARRAY_TOO_LARGE[0])

    # ========== Tests validate_date ==========

    def test_validate_date_valid(self):
        """Test date valide"""
        valid, value, error = self.validator.validate_date('2024-01-15', 'start_date')
        self.assertTrue(valid)
        self.assertEqual(value, date(2024, 1, 15))

    def test_validate_date_invalid_format(self):
        """Test date format invalide"""
        valid, value, error = self.validator.validate_date('15/01/2024', 'start_date')
        self.assertFalse(valid)
        self.assertEqual(error['code'], self.error_codes.VALIDATION_INVALID_DATE[0])

    def test_validate_date_with_min(self):
        """Test date avec minimum"""
        min_date = date(2024, 1, 10)
        valid, value, error = self.validator.validate_date('2024-01-05', 'start_date', min_date=min_date)
        self.assertFalse(valid)
        self.assertEqual(error['code'], self.error_codes.VALIDATION_INVALID_VALUE[0])

    def test_validate_date_optional_empty(self):
        """Test date optionnelle vide"""
        valid, value, error = self.validator.validate_date('', 'start_date', required=False)
        self.assertTrue(valid)
        self.assertIsNone(value)

    # ========== Tests validate_date_range ==========

    def test_validate_date_range_valid(self):
        """Test plage de dates valide"""
        valid, error = self.validator.validate_date_range(date(2024, 1, 1), date(2024, 1, 31))
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_validate_date_range_invalid(self):
        """Test plage de dates invalide (début > fin)"""
        valid, error = self.validator.validate_date_range(date(2024, 1, 31), date(2024, 1, 1))
        self.assertFalse(valid)
        self.assertEqual(error['code'], self.error_codes.VALIDATION_INVALID_DATE_RANGE[0])

    # ========== Tests validate_pagination ==========

    def test_validate_pagination_defaults(self):
        """Test pagination avec valeurs par défaut"""
        page, limit, offset = self.validator.validate_pagination(None, None)
        self.assertEqual(page, 1)
        self.assertEqual(limit, 20)
        self.assertEqual(offset, 0)

    def test_validate_pagination_custom_values(self):
        """Test pagination avec valeurs personnalisées"""
        page, limit, offset = self.validator.validate_pagination('3', '50')
        self.assertEqual(page, 3)
        self.assertEqual(limit, 50)
        self.assertEqual(offset, 100)

    def test_validate_pagination_max_limit(self):
        """Test pagination avec limit au-dessus du max"""
        page, limit, offset = self.validator.validate_pagination('1', '500', max_limit=100)
        self.assertEqual(limit, 100)

    def test_validate_pagination_invalid_values(self):
        """Test pagination avec valeurs invalides"""
        page, limit, offset = self.validator.validate_pagination('abc', 'xyz')
        self.assertEqual(page, 1)
        self.assertEqual(limit, 20)

    # ========== Tests security checks ==========

    def test_check_sql_injection(self):
        """Test détection injection SQL"""
        self.assertTrue(self.validator.check_sql_injection("'; DROP TABLE users;--"))
        self.assertTrue(self.validator.check_sql_injection("1' OR '1'='1"))
        self.assertFalse(self.validator.check_sql_injection("normal text"))

    def test_check_xss(self):
        """Test détection XSS"""
        self.assertTrue(self.validator.check_xss("<script>alert('xss')</script>"))
        self.assertTrue(self.validator.check_xss("onclick=alert(1)"))
        self.assertFalse(self.validator.check_xss("normal text"))

    def test_sanitize_string(self):
        """Test sanitisation de chaîne"""
        result = self.validator.sanitize_string("<script>test</script>")
        self.assertNotIn('<script>', result)
        self.assertIn('&lt;script&gt;', result)


class TestRateLimiter(TransactionCase):
    """Tests pour le rate limiter"""

    def setUp(self):
        super().setUp()
        from ..controllers.api_utils import SlidingWindowRateLimiter
        self.limiter = SlidingWindowRateLimiter()
        self.limiter.reset('test_ip')

    def test_rate_limiter_allows_requests(self):
        """Test que les requêtes sont autorisées sous la limite"""
        for i in range(5):
            is_limited, _ = self.limiter.is_rate_limited('test_ip', max_requests=10)
            self.assertFalse(is_limited)

    def test_rate_limiter_blocks_excess(self):
        """Test que les requêtes excessives sont bloquées"""
        for i in range(5):
            self.limiter.is_rate_limited('test_ip_block', max_requests=5)
        
        is_limited, remaining = self.limiter.is_rate_limited('test_ip_block', max_requests=5)
        self.assertTrue(is_limited)
        self.assertGreater(remaining, 0)

    def test_rate_limiter_reset(self):
        """Test réinitialisation du compteur"""
        for i in range(5):
            self.limiter.is_rate_limited('test_reset', max_requests=5)
        
        self.limiter.reset('test_reset')
        is_limited, _ = self.limiter.is_rate_limited('test_reset', max_requests=5)
        self.assertFalse(is_limited)

    def test_rate_limiter_stats(self):
        """Test obtention des statistiques"""
        for i in range(3):
            self.limiter.is_rate_limited('test_stats', max_requests=10)
        
        stats = self.limiter.get_stats('test_stats')
        self.assertEqual(stats['requests_count'], 3)
        self.assertFalse(stats['is_blocked'])


class TestCircuitBreaker(TransactionCase):
    """Tests pour le circuit breaker"""

    def setUp(self):
        super().setUp()
        from ..controllers.api_utils import CircuitBreaker, CircuitBreakerState
        # Utiliser un nom unique pour éviter les conflits entre tests
        self.breaker = CircuitBreaker(f'test_breaker_{id(self)}', failure_threshold=3, recovery_timeout=1)
        self.breaker.reset()
        self.CircuitBreakerState = CircuitBreakerState

    def test_circuit_breaker_closed_initially(self):
        """Test état initial fermé"""
        self.assertEqual(self.breaker.state, self.CircuitBreakerState.CLOSED)
        self.assertTrue(self.breaker.allow_request())

    def test_circuit_breaker_opens_after_failures(self):
        """Test ouverture après échecs"""
        for i in range(3):
            self.breaker.record_failure()
        
        self.assertEqual(self.breaker.state, self.CircuitBreakerState.OPEN)
        self.assertFalse(self.breaker.allow_request())

    def test_circuit_breaker_success_reduces_failures(self):
        """Test que le succès réduit le compteur d'échecs"""
        self.breaker.record_failure()
        self.breaker.record_failure()
        self.breaker.record_success()
        
        # Le circuit devrait toujours être fermé car le compteur est réduit
        self.assertEqual(self.breaker.state, self.CircuitBreakerState.CLOSED)

    def test_circuit_breaker_status(self):
        """Test obtention du statut"""
        self.breaker.record_failure()
        
        status = self.breaker.get_status()
        self.assertEqual(status['name'], self.breaker.name)
        self.assertEqual(status['state'], 'closed')
        self.assertEqual(status['failure_count'], 1)


class TestApiResponse(TransactionCase):
    """Tests pour les helpers de réponse API"""

    def test_api_response_success(self):
        """Test réponse succès"""
        from ..controllers.api_utils import api_response, API_VERSION
        
        response = api_response(data={'key': 'value'}, message='Success')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['api_version'], API_VERSION)
        self.assertEqual(data['data'], {'key': 'value'})
        self.assertEqual(data['message'], 'Success')

    def test_api_error_response(self):
        """Test réponse erreur"""
        from ..controllers.api_utils import api_error, APIErrorCodes
        
        response = api_error(APIErrorCodes.RESOURCE_NOT_FOUND, status=404)
        
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertEqual(data['error']['code'], 'RES_001')

    def test_api_validation_error_response(self):
        """Test réponse erreur de validation"""
        from ..controllers.api_utils import api_validation_error
        
        errors = [
            {'field': 'email', 'message': 'Email invalide'},
            {'field': 'password', 'message': 'Mot de passe requis'}
        ]
        
        response = api_validation_error(errors)
        
        self.assertEqual(response.status_code, 422)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertEqual(data['error']['code'], 'VALIDATION_ERROR')
        self.assertEqual(len(data['error']['details']), 2)

    def test_security_headers_present(self):
        """Test présence des headers de sécurité"""
        from ..controllers.api_utils import api_response
        
        response = api_response(data={})
        
        self.assertIn('X-Content-Type-Options', response.headers)
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertIn('X-Frame-Options', response.headers)
        self.assertIn('Cache-Control', response.headers)
