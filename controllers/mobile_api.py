# -*- coding: utf-8 -*-
"""
API REST Mobile pour le PDG - Potting Management
Module: potting_management
Version: 1.1.0

Cette API permet au PDG de:
- Consulter le tableau de bord des activités d'exportation
- Visualiser les statistiques en temps réel
- Télécharger le rapport quotidien en PDF

Endpoints:
- POST /api/v1/potting/auth/login - Authentification
- POST /api/v1/potting/auth/logout - Déconnexion
- GET /api/v1/potting/dashboard - Tableau de bord principal
- GET /api/v1/potting/dashboard/orders - Liste des commandes
- GET /api/v1/potting/dashboard/transit-orders - Liste des OT
- GET /api/v1/potting/reports/daily - Télécharger rapport quotidien PDF
- GET /api/v1/potting/reports/summary - Résumé du rapport (JSON)
- GET /api/v1/potting/health - Vérification de santé

Améliorations v1.1.0:
- Exception handler global
- Validation robuste des entrées
- Rate limiting amélioré
- Circuit breaker pour les rapports
- Correlation ID pour le tracing
- Headers de sécurité
"""

import base64
import logging
import hashlib
import secrets
from datetime import datetime, timedelta, date
import re

from odoo import http, _, fields
from odoo.http import request, Response
import json

from .api_utils import (
    APIErrorCodes,
    rate_limiter, rate_limit, rate_limit_user,
    InputValidator,
    api_response, api_error, api_validation_error,
    API_VERSION,
    require_auth, require_ceo_auth,
    api_exception_handler,
    with_circuit_breaker, report_circuit_breaker,
    get_client_ip, log_api_call,
    format_currency,
    RequestContext
)

_logger = logging.getLogger(__name__)

# Configuration
TOKEN_EXPIRY_HOURS = 24 * 7  # 7 jours
MAX_LOGIN_ATTEMPTS = 5


class PottingMobileAPIController(http.Controller):
    """Contrôleur API REST pour l'application mobile Flutter du PDG"""

    # ==================== UTILITAIRES INTERNES ====================

    def _generate_api_token(self):
        """Générer un token API sécurisé"""
        return secrets.token_urlsafe(64)

    def _hash_token(self, token):
        """Hasher un token pour le stockage"""
        return hashlib.sha256(token.encode()).hexdigest()

    def _verify_api_token(self, token):
        """Vérifier un token API et retourner l'utilisateur associé"""
        try:
            token_hash = self._hash_token(token)
            
            # Chercher le token dans ir.config_parameter ou une table dédiée
            ApiToken = request.env['potting.api.token'].sudo()
            token_record = ApiToken.search([
                ('token_hash', '=', token_hash),
                ('expires_at', '>', fields.Datetime.now()),
                ('is_active', '=', True)
            ], limit=1)
            
            if token_record and token_record.user_id.active:
                # Mettre à jour la dernière utilisation
                token_record.write({'last_used': fields.Datetime.now()})
                return token_record.user_id
            
            return False
        except Exception as e:
            _logger.error(f"Erreur vérification token API potting: {e}")
            return False

    def _format_transit_order(self, ot, include_details=False):
        """Formater un OT pour l'API"""
        data = {
            'id': ot.id,
            'name': ot.name,
            'reference': ot.ot_reference or '',
            'customer': ot.customer_id.name if ot.customer_id else '',
            'consignee': ot.consignee_id.name if ot.consignee_id else '',
            'product_type': ot.product_type,
            'product_type_label': dict(ot._fields['product_type'].selection).get(ot.product_type, '') if ot.product_type else '',
            'tonnage': ot.tonnage,
            'tonnage_kg': ot.tonnage * 1000,
            'current_tonnage': ot.current_tonnage,
            'current_tonnage_kg': ot.current_tonnage * 1000,
            'progress_percentage': round(ot.progress_percentage, 1),
            'state': ot.state,
            'state_label': dict(ot._fields['state'].selection).get(ot.state, ''),
            'delivery_status': ot.delivery_status,
            'date_created': ot.date_created.isoformat() if ot.date_created else None,
        }
        
        if include_details:
            data.update({
                'formule_reference': ot.formule_reference or '',
                'lot_count': ot.lot_count,
                'container_count': ot.container_count if hasattr(ot, 'container_count') else 0,
                'delivered_tonnage': ot.delivered_tonnage,
                'remaining_to_deliver_tonnage': ot.remaining_to_deliver_tonnage,
                'date_validated': ot.date_validated.isoformat() if ot.date_validated else None,
                'note': ot.note or '',
            })
        
        return data

    def _format_customer_order(self, order, include_details=False):
        """Formater une commande client pour l'API"""
        data = {
            'id': order.id,
            'name': order.name,
            'contract_number': order.contract_number or '',
            'customer': order.customer_id.name if order.customer_id else '',
            'product_type': order.product_type,
            'product_type_label': dict(order._fields['product_type'].selection).get(order.product_type, '') if order.product_type else '',
            'contract_tonnage': order.contract_tonnage,
            'allocated_tonnage': order.allocated_tonnage,
            'remaining_contract_tonnage': order.remaining_contract_tonnage,
            'progress_percentage': round(order.progress_percentage, 1) if hasattr(order, 'progress_percentage') else 0,
            'state': order.state,
            'state_label': dict(order._fields['state'].selection).get(order.state, ''),
            'date_order': order.date_order.isoformat() if order.date_order else None,
        }
        
        if include_details:
            data.update({
                'cv_reference': order.cv_reference or '',
                'transit_order_count': order.transit_order_count,
                'note': order.note or '',
            })
        
        return data

    def _get_dashboard_stats(self, date_from=None, date_to=None):
        """Calculer les statistiques du tableau de bord"""
        TransitOrder = request.env['potting.transit.order'].sudo()
        CustomerOrder = request.env['potting.customer.order'].sudo()
        Lot = request.env['potting.lot'].sudo()
        
        # Domaines de base
        ot_domain = [('state', 'not in', ['draft', 'cancelled'])]
        order_domain = [('state', 'not in', ['cancelled'])]
        
        if date_from:
            ot_domain.append(('date_created', '>=', date_from))
            order_domain.append(('date_order', '>=', date_from))
        if date_to:
            ot_domain.append(('date_created', '<=', date_to))
            order_domain.append(('date_order', '<=', date_to))
        
        # Récupérer les données
        transit_orders = TransitOrder.search(ot_domain)
        customer_orders = CustomerOrder.search(order_domain)
        
        # Statistiques OT
        total_ot = len(transit_orders)
        ot_done = len(transit_orders.filtered(lambda o: o.state == 'done'))
        ot_in_progress = len(transit_orders.filtered(lambda o: o.state in ['in_progress', 'lots_generated']))
        ot_ready_validation = len(transit_orders.filtered(lambda o: o.state == 'ready_validation'))
        
        # Statistiques production
        total_tonnage = sum(transit_orders.mapped('tonnage'))
        current_tonnage = sum(transit_orders.mapped('current_tonnage'))
        avg_progress = sum(transit_orders.mapped('progress_percentage')) / total_ot if total_ot else 0
        
        # Statistiques par type de produit
        product_stats = {}
        for product_type in ['cocoa_mass', 'cocoa_butter', 'cocoa_cake', 'cocoa_powder']:
            ots = transit_orders.filtered(lambda o: o.product_type == product_type)
            if ots:
                product_stats[product_type] = {
                    'count': len(ots),
                    'tonnage': sum(ots.mapped('tonnage')),
                    'current_tonnage': sum(ots.mapped('current_tonnage')),
                    'avg_progress': sum(ots.mapped('progress_percentage')) / len(ots)
                }
        
        # Statistiques livraison
        fully_delivered = len(transit_orders.filtered(lambda o: o.delivery_status == 'fully_delivered'))
        partial_delivery = len(transit_orders.filtered(lambda o: o.delivery_status == 'partial'))
        not_delivered = len(transit_orders.filtered(lambda o: o.delivery_status == 'not_delivered'))
        
        # Top clients
        customer_ot_count = {}
        for ot in transit_orders:
            customer_name = ot.customer_id.name if ot.customer_id else 'Non défini'
            if customer_name not in customer_ot_count:
                customer_ot_count[customer_name] = {'count': 0, 'tonnage': 0}
            customer_ot_count[customer_name]['count'] += 1
            customer_ot_count[customer_name]['tonnage'] += ot.tonnage
        
        top_customers = sorted(
            [{'name': k, **v} for k, v in customer_ot_count.items()],
            key=lambda x: x['tonnage'],
            reverse=True
        )[:5]
        
        return {
            'summary': {
                'total_transit_orders': total_ot,
                'total_customer_orders': len(customer_orders),
                'total_tonnage': round(total_tonnage, 2),
                'total_tonnage_kg': round(total_tonnage * 1000, 0),
                'current_tonnage': round(current_tonnage, 2),
                'current_tonnage_kg': round(current_tonnage * 1000, 0),
                'average_progress': round(avg_progress, 1),
            },
            'transit_orders_by_state': {
                'done': ot_done,
                'in_progress': ot_in_progress,
                'ready_validation': ot_ready_validation,
            },
            'delivery_status': {
                'fully_delivered': fully_delivered,
                'partial': partial_delivery,
                'not_delivered': not_delivered,
            },
            'by_product_type': product_stats,
            'top_customers': top_customers,
        }

    # ==================== ENDPOINTS AUTHENTIFICATION ====================

    @http.route('/api/v1/potting/auth/login', type='json', auth='none', methods=['POST'], csrf=False, cors='*')
    @rate_limit(max_requests=MAX_LOGIN_ATTEMPTS, window_seconds=300)
    def api_login(self, **kwargs):
        """
        Authentification du PDG.
        
        Body JSON:
        {
            "login": "email@example.com",
            "password": "secret"
        }
        
        Returns:
        {
            "success": true,
            "data": {
                "token": "xxx",
                "expires_at": "2024-01-15T10:00:00",
                "user": {...}
            }
        }
        """
        try:
            # Récupérer les données JSON
            data = request.jsonrequest
            login = data.get('login', '').strip()
            password = data.get('password', '')
            
            # Validation
            if not login:
                return {
                    'success': False,
                    'error': {'code': 'VAL_001', 'message': "L'identifiant est requis"}
                }
            
            if not password:
                return {
                    'success': False,
                    'error': {'code': 'VAL_001', 'message': "Le mot de passe est requis"}
                }
            
            # Authentifier l'utilisateur via Odoo
            try:
                uid = request.session.authenticate(request.db, login, password)
            except Exception as auth_error:
                _logger.warning(f"Échec authentification potting API: {login} - {auth_error}")
                return {
                    'success': False,
                    'error': {'code': 'AUTH_005', 'message': "Identifiants incorrects"}
                }
            
            if not uid:
                log_api_call('/auth/login', success=False, details=f"login={login}")
                return {
                    'success': False,
                    'error': {'code': 'AUTH_005', 'message': "Identifiants incorrects"}
                }
            
            user = request.env['res.users'].sudo().browse(uid)
            
            # Vérifier que l'utilisateur a les droits potting
            has_potting_access = user.has_group('potting_management.group_potting_user')
            if not has_potting_access:
                return {
                    'success': False,
                    'error': {'code': 'AUTH_007', 'message': "Accès non autorisé au module Exportation"}
                }
            
            # Générer le token
            token = self._generate_api_token()
            token_hash = self._hash_token(token)
            expires_at = datetime.now() + timedelta(hours=TOKEN_EXPIRY_HOURS)
            
            # Sauvegarder le token
            ApiToken = request.env['potting.api.token'].sudo()
            
            # Désactiver les anciens tokens de cet utilisateur
            ApiToken.search([('user_id', '=', uid)]).write({'is_active': False})
            
            # Créer le nouveau token
            ApiToken.create({
                'user_id': uid,
                'token_hash': token_hash,
                'expires_at': expires_at,
                'is_active': True,
                'device_info': request.httprequest.headers.get('User-Agent', '')[:200],
                'ip_address': get_client_ip(),
            })
            
            log_api_call('/auth/login', user_id=uid, success=True)
            
            # Déterminer le rôle de l'utilisateur
            roles = []
            if user.has_group('potting_management.group_potting_manager'):
                roles.append('manager')
            if user.has_group('potting_management.group_potting_ceo_agent'):
                roles.append('export_agent')
            if user.has_group('potting_management.group_potting_shipping'):
                roles.append('shipping')
            if user.has_group('potting_management.group_potting_commercial'):
                roles.append('commercial')
            
            return {
                'success': True,
                'data': {
                    'token': token,
                    'token_type': 'Bearer',
                    'expires_at': expires_at.isoformat(),
                    'user': {
                        'id': user.id,
                        'name': user.name,
                        'email': user.email or user.login,
                        'roles': roles,
                        'company': user.company_id.name,
                    }
                }
            }
            
        except Exception as e:
            _logger.exception(f"Erreur login API potting: {e}")
            return {
                'success': False,
                'error': {'code': 'SRV_001', 'message': "Erreur technique, veuillez réessayer"}
            }

    @http.route('/api/v1/potting/auth/logout', type='json', auth='none', methods=['POST'], csrf=False, cors='*')
    def api_logout(self, **kwargs):
        """Déconnexion - Invalider le token"""
        try:
            auth_header = request.httprequest.headers.get('Authorization', '')
            
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
                token_hash = self._hash_token(token)
                
                ApiToken = request.env['potting.api.token'].sudo()
                token_record = ApiToken.search([('token_hash', '=', token_hash)], limit=1)
                if token_record:
                    token_record.write({'is_active': False})
                    log_api_call('/auth/logout', user_id=token_record.user_id.id, success=True)
            
            return {
                'success': True,
                'message': "Déconnexion réussie"
            }
            
        except Exception as e:
            _logger.exception(f"Erreur logout API potting: {e}")
            return {
                'success': True,
                'message': "Déconnexion réussie"
            }

    # ==================== ENDPOINTS DASHBOARD ====================

    @http.route('/api/v1/potting/dashboard', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @api_exception_handler
    @rate_limit(max_requests=60, window_seconds=60)
    @require_auth
    def api_dashboard(self, **kwargs):
        """
        Tableau de bord principal du PDG.
        
        Query params:
        - date_from: Date début (YYYY-MM-DD)
        - date_to: Date fin (YYYY-MM-DD)
        
        Returns:
        {
            "success": true,
            "data": {
                "summary": {...},
                "transit_orders_by_state": {...},
                "delivery_status": {...},
                "by_product_type": {...},
                "top_customers": [...]
            }
        }
        """
        # L'utilisateur est déjà authentifié par @require_auth (stocké dans request.api_user)
        user = request.api_user
        
        # Parser les paramètres de date
        date_from = kwargs.get('date_from')
        date_to = kwargs.get('date_to')
        
        parsed_from = None
        parsed_to = None
        
        if date_from:
            valid, parsed_from, error = InputValidator.validate_date(date_from, 'date_from', required=False)
            if not valid:
                return api_validation_error(error)
        
        if date_to:
            valid, parsed_to, error = InputValidator.validate_date(date_to, 'date_to', required=False)
            if not valid:
                return api_validation_error(error)
        
        if parsed_from and parsed_to:
            valid, error = InputValidator.validate_date_range(parsed_from, parsed_to)
            if not valid:
                return api_validation_error(error)
        
        # Calculer les statistiques
        stats = self._get_dashboard_stats(parsed_from, parsed_to)
        
        log_api_call('/dashboard', user_id=user.id, success=True)
        
        return api_response(
            data=stats,
            meta={
                'date_from': date_from,
                'date_to': date_to,
                'generated_at': datetime.now().isoformat()
            }
        )

    @http.route('/api/v1/potting/dashboard/transit-orders', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @api_exception_handler
    @rate_limit(max_requests=60, window_seconds=60)
    @require_auth
    def api_transit_orders_list(self, **kwargs):
        """
        Liste des ordres de transit.
        
        Query params:
        - date_from: Date début
        - date_to: Date fin
        - state: Filtrer par état (draft, in_progress, done, etc.)
        - product_type: Filtrer par type de produit
        - customer_id: Filtrer par client
        - page: Numéro de page (défaut: 1)
        - limit: Nombre par page (défaut: 20, max: 100)
        - include_details: Inclure les détails (0 ou 1)
        """
        user = request.api_user
        
        # Construire le domaine de recherche
        domain = [('state', '!=', 'cancelled')]
        
        # Filtres de date
        date_from = kwargs.get('date_from')
        date_to = kwargs.get('date_to')
        
        if date_from:
            valid, parsed, error = InputValidator.validate_date(date_from, 'date_from', required=False)
            if valid and parsed:
                domain.append(('date_created', '>=', parsed))
        
        if date_to:
            valid, parsed, error = InputValidator.validate_date(date_to, 'date_to', required=False)
            if valid and parsed:
                domain.append(('date_created', '<=', parsed))
        
        # Autres filtres avec validation
        state = kwargs.get('state')
        if state:
            valid, state, error = InputValidator.validate_enum(
                state, 'state', 
                ['draft', 'in_progress', 'lots_generated', 'ready_validation', 'done', 'cancelled'],
                required=False
            )
            if valid and state:
                domain.append(('state', '=', state))
        
        product_type = kwargs.get('product_type')
        if product_type:
            valid, product_type, error = InputValidator.validate_enum(
                product_type, 'product_type',
                ['cocoa_mass', 'cocoa_butter', 'cocoa_cake', 'cocoa_powder'],
                required=False
            )
            if valid and product_type:
                domain.append(('product_type', '=', product_type))
        
        customer_id = kwargs.get('customer_id')
        if customer_id:
            valid, customer_id, error = InputValidator.validate_id(customer_id, 'customer_id', required=False)
            if valid and customer_id:
                domain.append(('customer_id', '=', customer_id))
        
        # Pagination avec validation
        page, limit, offset = InputValidator.validate_pagination(
            kwargs.get('page'), kwargs.get('limit')
        )
        include_details = kwargs.get('include_details', '0') == '1'
        
        # Rechercher les OT
        TransitOrder = request.env['potting.transit.order'].sudo()
        total_count = TransitOrder.search_count(domain)
        transit_orders = TransitOrder.search(domain, order='name desc', limit=limit, offset=offset)
        
        # Formater les données
        items = [self._format_transit_order(ot, include_details) for ot in transit_orders]
        
        log_api_call('/dashboard/transit-orders', user_id=user.id, success=True)
        
        return api_response(
            data={'items': items},
            meta={
                'total': total_count,
                'page': page,
                'limit': limit,
                'pages': (total_count + limit - 1) // limit
            }
        )

    @http.route('/api/v1/potting/dashboard/orders', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @api_exception_handler
    @rate_limit(max_requests=60, window_seconds=60)
    @require_auth
    def api_customer_orders_list(self, **kwargs):
        """
        Liste des commandes clients (contrats).
        
        Query params identiques à transit-orders.
        """
        user = request.api_user
        
        # Construire le domaine
        domain = [('state', '!=', 'cancelled')]
        
        date_from = kwargs.get('date_from')
        date_to = kwargs.get('date_to')
        
        if date_from:
            valid, parsed, error = InputValidator.validate_date(date_from, 'date_from', required=False)
            if valid and parsed:
                domain.append(('date_order', '>=', parsed))
        
        if date_to:
            valid, parsed, error = InputValidator.validate_date(date_to, 'date_to', required=False)
            if valid and parsed:
                domain.append(('date_order', '<=', parsed))
        
        state = kwargs.get('state')
        if state:
            valid, state, error = InputValidator.validate_enum(
                state, 'state',
                ['draft', 'confirmed', 'in_progress', 'done', 'cancelled'],
                required=False
            )
            if valid and state:
                domain.append(('state', '=', state))
        
        product_type = kwargs.get('product_type')
        if product_type:
            valid, product_type, error = InputValidator.validate_enum(
                product_type, 'product_type',
                ['cocoa_mass', 'cocoa_butter', 'cocoa_cake', 'cocoa_powder'],
                required=False
            )
            if valid and product_type:
                domain.append(('product_type', '=', product_type))
        
        # Pagination avec validation
        page, limit, offset = InputValidator.validate_pagination(
            kwargs.get('page'), kwargs.get('limit')
        )
        include_details = kwargs.get('include_details', '0') == '1'
        
        # Rechercher
        CustomerOrder = request.env['potting.customer.order'].sudo()
        total_count = CustomerOrder.search_count(domain)
        orders = CustomerOrder.search(domain, order='create_date desc', limit=limit, offset=offset)
        
        items = [self._format_customer_order(order, include_details) for order in orders]
        
        log_api_call('/dashboard/orders', user_id=user.id, success=True)
        
        return api_response(
            data={'items': items},
            meta={
                'total': total_count,
                'page': page,
                'limit': limit,
                'pages': (total_count + limit - 1) // limit
            }
        )

    # ==================== ENDPOINTS RAPPORTS ====================

    @http.route('/api/v1/potting/reports/summary', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @api_exception_handler
    @rate_limit(max_requests=30, window_seconds=60)
    @require_auth
    def api_report_summary(self, **kwargs):
        """
        Résumé du rapport quotidien en JSON.
        
        Query params:
        - date: Date du rapport (défaut: aujourd'hui)
        - date_from: Date début pour les OT
        - date_to: Date fin pour les OT
        - exclude_fully_delivered: Exclure les OT livrés (0 ou 1, défaut: 1)
        """
        user = request.api_user
        
        # Paramètres
        report_date = kwargs.get('date')
        if report_date:
            valid, parsed_date, error = InputValidator.validate_date(report_date, 'date')
            if not valid:
                return api_validation_error(error)
            report_date = parsed_date
        else:
            report_date = date.today()
        
        date_from = kwargs.get('date_from')
        date_to = kwargs.get('date_to')
        exclude_fully_delivered = kwargs.get('exclude_fully_delivered', '1') == '1'
        
        # Construire le domaine
        domain = [('state', 'not in', ['draft', 'cancelled'])]
        
        if date_from:
            valid, parsed, _ = InputValidator.validate_date(date_from, 'date_from', required=False)
            if valid and parsed:
                domain.append(('date_created', '>=', parsed))
        else:
            # Par défaut, les 30 derniers jours
            domain.append(('date_created', '>=', date.today() - timedelta(days=30)))
        
        if date_to:
            valid, parsed, _ = InputValidator.validate_date(date_to, 'date_to', required=False)
            if valid and parsed:
                domain.append(('date_created', '<=', parsed))
        
        if exclude_fully_delivered:
            domain.append(('delivery_status', '!=', 'fully_delivered'))
        
        # Récupérer les OT
        TransitOrder = request.env['potting.transit.order'].sudo()
        transit_orders = TransitOrder.search(domain, order='name asc')
        
        if not transit_orders:
            return api_response(
                data={
                    'report_date': report_date.isoformat(),
                    'message': 'Aucun OT trouvé pour les critères spécifiés',
                    'ot_count': 0
                }
            )
        
        # Calculer les statistiques
        total_tonnage_kg = sum(transit_orders.mapped('tonnage')) * 1000
        current_tonnage_kg = sum(transit_orders.mapped('current_tonnage')) * 1000
        avg_progress = sum(transit_orders.mapped('progress_percentage')) / len(transit_orders)
        
        # Par état
        in_tc = len(transit_orders.filtered(lambda o: o.state == 'done'))
        prod_100 = len(transit_orders.filtered(lambda o: o.progress_percentage >= 100 and o.state != 'done'))
        in_prod = len(transit_orders.filtered(lambda o: o.progress_percentage < 100 and o.state not in ['done', 'cancelled']))
        
        # Par livraison
        partial_delivery = len(transit_orders.filtered(lambda o: o.delivery_status == 'partial'))
        fully_delivered = len(transit_orders.filtered(lambda o: o.delivery_status == 'fully_delivered'))
        not_delivered = len(transit_orders.filtered(lambda o: o.delivery_status == 'not_delivered'))
        
        # Extraire la plage de numéros OT
        ot_numbers = []
        for ot in transit_orders:
            match = re.search(r'(\d+)/', ot.name)
            if match:
                ot_numbers.append(int(match.group(1)))
        
        ot_range = {}
        if ot_numbers:
            ot_range = {'from': min(ot_numbers), 'to': max(ot_numbers)}
        
        # Grouper par client
        customers = {}
        for ot in transit_orders:
            customer_name = ot.customer_id.name if ot.customer_id else 'Non défini'
            consignee_name = ot.consignee_id.name if ot.consignee_id else ''
            key = f"{customer_name} / {consignee_name}" if consignee_name else customer_name
            
            if key not in customers:
                customers[key] = {'count': 0, 'tonnage': 0}
            customers[key]['count'] += 1
            customers[key]['tonnage'] += ot.tonnage * 1000
        
        log_api_call('/reports/summary', user_id=user.id, success=True)
        
        return api_response(
            data={
                'report_date': report_date.isoformat(),
                'generated_at': datetime.now().isoformat(),
                'ot_count': len(transit_orders),
                'ot_range': ot_range,
                'tonnage': {
                    'total_kg': round(total_tonnage_kg, 0),
                    'current_kg': round(current_tonnage_kg, 0),
                    'total_formatted': format_currency(total_tonnage_kg, 'Kg'),
                    'current_formatted': format_currency(current_tonnage_kg, 'Kg'),
                },
                'average_progress': round(avg_progress, 1),
                'by_production_state': {
                    'in_tc': in_tc,
                    'production_100': prod_100,
                    'in_production': in_prod,
                },
                'by_delivery_status': {
                    'fully_delivered': fully_delivered,
                    'partial': partial_delivery,
                    'not_delivered': not_delivered,
                },
                'by_customer': [
                    {'name': k, **v} for k, v in sorted(
                        customers.items(),
                        key=lambda x: x[1]['tonnage'],
                        reverse=True
                    )
                ]
            }
        )

    @http.route('/api/v1/potting/reports/daily', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @api_exception_handler
    @rate_limit(max_requests=10, window_seconds=60)
    @require_auth
    @with_circuit_breaker(report_circuit_breaker)
    def api_download_daily_report(self, **kwargs):
        """
        Télécharger le rapport quotidien en PDF.
        
        Query params:
        - date: Date du rapport (défaut: aujourd'hui)
        - date_from: Date début pour les OT
        - date_to: Date fin pour les OT
        - exclude_fully_delivered: Exclure les OT livrés (0 ou 1, défaut: 1)
        
        Returns:
        - Application/pdf - Le fichier PDF du rapport
        """
        user = request.api_user
        
        # Paramètres
        report_date = kwargs.get('date')
        if report_date:
            valid, parsed_date, error = InputValidator.validate_date(report_date, 'date')
            if not valid:
                return api_validation_error(error)
            report_date = parsed_date
        else:
            report_date = date.today()
        
        date_from_str = kwargs.get('date_from')
        date_to_str = kwargs.get('date_to')
        exclude_fully_delivered = kwargs.get('exclude_fully_delivered', '1') == '1'
        
        # Créer un wizard temporaire pour générer le rapport
        Wizard = request.env['potting.daily.report.wizard'].sudo()
        
        wizard_vals = {
            'report_date': report_date,
            'exclude_fully_delivered': exclude_fully_delivered,
        }
        
        if date_from_str:
            valid, parsed, _ = InputValidator.validate_date(date_from_str, 'date_from', required=False)
            if valid and parsed:
                wizard_vals['date_from'] = parsed
        
        if date_to_str:
            valid, parsed, _ = InputValidator.validate_date(date_to_str, 'date_to', required=False)
            if valid and parsed:
                wizard_vals['date_to'] = parsed
        
        wizard = Wizard.create(wizard_vals)
        
        # Vérifier qu'il y a des OT
        if not wizard.transit_order_ids:
            wizard.unlink()
            return api_error(
                APIErrorCodes.BUSINESS_NO_TRANSIT_ORDERS,
                "Aucun OT trouvé pour les critères spécifiés",
                status=404
            )
        
        # Générer le PDF
        report = request.env.ref('potting_management.action_report_ot_daily').sudo()
        pdf_content, _ = report._render_qweb_pdf(report.id, [wizard.id])
        
        if not pdf_content:
            wizard.unlink()
            return api_error(
                APIErrorCodes.BUSINESS_REPORT_GENERATION_FAILED,
                status=500
            )
        
        ot_count = len(wizard.transit_order_ids)
        log_api_call('/reports/daily', user_id=user.id, success=True, 
                    details=f"date={report_date}, ot_count={ot_count}")
        
        # Nettoyer le wizard
        wizard.unlink()
        
        # Retourner le PDF
        filename = f"OT_Daily_Report_{report_date.strftime('%Y-%m-%d')}.pdf"
        
        return Response(
            pdf_content,
            headers={
                'Content-Type': 'application/pdf',
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Length': len(pdf_content),
                'X-Content-Type-Options': 'nosniff',
            },
            status=200
        )

    @http.route('/api/v1/potting/transit-orders/<int:ot_id>', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @api_exception_handler
    @rate_limit(max_requests=60, window_seconds=60)
    @require_auth
    def api_transit_order_detail(self, ot_id, **kwargs):
        """
        Détails d'un ordre de transit spécifique.
        """
        user = request.api_user
        
        # Validation de l'ID
        valid, ot_id, error = InputValidator.validate_id(ot_id, 'ot_id')
        if not valid:
            return api_validation_error(error)
        
        # Récupérer l'OT
        TransitOrder = request.env['potting.transit.order'].sudo()
        ot = TransitOrder.browse(ot_id)
        
        if not ot.exists():
            return api_error(APIErrorCodes.RESOURCE_NOT_FOUND, status=404)
        
        # Formater avec tous les détails
        data = self._format_transit_order(ot, include_details=True)
        
        # Ajouter les lots
        data['lots'] = [{
            'id': lot.id,
            'name': lot.name,
            'product_type': lot.product_type,
            'target_tonnage': lot.target_tonnage,
            'current_tonnage': lot.current_tonnage,
            'fill_percentage': round(lot.fill_percentage, 1),
            'state': lot.state,
            'state_label': dict(lot._fields['state'].selection).get(lot.state, ''),
            'container': lot.container_id.name if lot.container_id else None,
        } for lot in ot.lot_ids]
        
        log_api_call(f'/transit-orders/{ot_id}', user_id=user.id, success=True)
        
        return api_response(data=data)

    # ==================== ENDPOINT SANTÉ ====================

    @http.route('/api/v1/potting/health', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    def api_health_check(self, **kwargs):
        """
        Vérification de santé de l'API.
        Endpoint public sans authentification.
        
        Retourne le statut de l'API et des services dépendants.
        """
        from .api_utils import db_circuit_breaker, report_circuit_breaker
        
        # Vérifier la connexion à la base de données
        db_status = 'healthy'
        try:
            request.env['res.users'].sudo().search_count([])
        except Exception:
            db_status = 'unhealthy'
        
        return api_response(
            data={
                'status': 'healthy' if db_status == 'healthy' else 'degraded',
                'api_version': API_VERSION,
                'module': 'potting_management',
                'timestamp': datetime.now().isoformat(),
                'services': {
                    'database': db_status,
                    'report_generation': report_circuit_breaker.state.value,
                },
                'circuit_breakers': {
                    'database': db_circuit_breaker.get_status(),
                    'report': report_circuit_breaker.get_status(),
                }
            }
        )
