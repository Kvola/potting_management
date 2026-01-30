/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Dashboard pour le profil Responsable CV/Formules
 * Focus sur la gestion des Confirmations de Vente et Formules (Réglementation CCC)
 */
export class PottingCvFormuleManagerDashboard extends Component {
    static template = "potting_management.CvFormuleManagerDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            // Campagne active
            currentCampaign: null,
            
            // Statistiques CV
            cvStats: {
                total: 0,
                active: 0,
                expired: 0,
                consumed: 0,
                tonnage_autorise: 0,
                tonnage_utilise: 0,
                tonnage_disponible: 0,
                expiring_soon: 0,
            },
            
            // Statistiques Formules
            formuleStats: {
                total: 0,
                draft: 0,
                validated: 0,
                partial_paid: 0,
                paid: 0,
                total_montant: 0,
                total_paye: 0,
                reste_a_payer: 0,
            },
            
            // CV récentes
            recentCVs: [],
            
            // CV expirant bientôt
            expiringCVs: [],
            
            // Formules à valider/payer
            formulesPending: [],
            
            // Résumé par type de produit
            productStats: [],
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        // Charger la campagne active
        try {
            const campaigns = await this.orm.searchRead(
                "potting.campaign",
                [['state', '=', 'active']],
                ["name", "code", "date_start", "date_end"],
                { limit: 1 }
            );
            if (campaigns.length > 0) {
                this.state.currentCampaign = campaigns[0];
            }
        } catch (e) {
            console.log("Campaign model not available");
        }

        await this.loadCVStats();
        await this.loadFormuleStats();
        await this.loadRecentData();
        await this.loadProductStats();
    }

    async loadCVStats() {
        try {
            // Total des CV
            this.state.cvStats.total = await this.orm.searchCount(
                "potting.confirmation.vente", []
            );

            // CV par état
            this.state.cvStats.active = await this.orm.searchCount(
                "potting.confirmation.vente",
                [['state', '=', 'active']]
            );
            this.state.cvStats.expired = await this.orm.searchCount(
                "potting.confirmation.vente",
                [['state', '=', 'expired']]
            );
            this.state.cvStats.consumed = await this.orm.searchCount(
                "potting.confirmation.vente",
                [['state', '=', 'consumed']]
            );

            // Tonnages CV
            const cvData = await this.orm.searchRead(
                "potting.confirmation.vente",
                [['state', 'in', ['draft', 'active']]],
                ["tonnage_autorise", "tonnage_utilise", "tonnage_disponible", "date_validite"]
            );
            
            this.state.cvStats.tonnage_autorise = cvData.reduce(
                (sum, cv) => sum + (cv.tonnage_autorise || 0), 0
            );
            this.state.cvStats.tonnage_utilise = cvData.reduce(
                (sum, cv) => sum + (cv.tonnage_utilise || 0), 0
            );
            this.state.cvStats.tonnage_disponible = cvData.reduce(
                (sum, cv) => sum + (cv.tonnage_disponible || 0), 0
            );

            // CV expirant dans 30 jours
            const thirtyDaysFromNow = new Date();
            thirtyDaysFromNow.setDate(thirtyDaysFromNow.getDate() + 30);
            const today = new Date().toISOString().split('T')[0];
            const futureDate = thirtyDaysFromNow.toISOString().split('T')[0];
            
            this.state.cvStats.expiring_soon = await this.orm.searchCount(
                "potting.confirmation.vente",
                [
                    ['state', '=', 'active'],
                    ['date_validite', '>=', today],
                    ['date_validite', '<=', futureDate]
                ]
            );
        } catch (e) {
            console.log("Error loading CV stats:", e);
        }
    }

    async loadFormuleStats() {
        try {
            // Total des formules
            this.state.formuleStats.total = await this.orm.searchCount(
                "potting.formule", []
            );

            // Formules par état
            const states = ['draft', 'validated', 'partial_paid', 'paid'];
            for (const state of states) {
                this.state.formuleStats[state] = await this.orm.searchCount(
                    "potting.formule",
                    [['state', '=', state]]
                );
            }

            // Montants des formules
            const formuleData = await this.orm.searchRead(
                "potting.formule",
                [],
                ["montant_total", "montant_paye", "reste_a_payer"]
            );
            
            this.state.formuleStats.total_montant = formuleData.reduce(
                (sum, f) => sum + (f.montant_total || 0), 0
            );
            this.state.formuleStats.total_paye = formuleData.reduce(
                (sum, f) => sum + (f.montant_paye || 0), 0
            );
            this.state.formuleStats.reste_a_payer = formuleData.reduce(
                (sum, f) => sum + (f.reste_a_payer || 0), 0
            );
        } catch (e) {
            console.log("Error loading Formule stats:", e);
        }
    }

    async loadRecentData() {
        try {
            // CV récentes
            this.state.recentCVs = await this.orm.searchRead(
                "potting.confirmation.vente",
                [],
                ["reference", "client_id", "tonnage_autorise", "tonnage_disponible", 
                 "date_validite", "state"],
                { limit: 5, order: "create_date desc" }
            );

            // CV expirant bientôt
            const thirtyDaysFromNow = new Date();
            thirtyDaysFromNow.setDate(thirtyDaysFromNow.getDate() + 30);
            const today = new Date().toISOString().split('T')[0];
            const futureDate = thirtyDaysFromNow.toISOString().split('T')[0];
            
            this.state.expiringCVs = await this.orm.searchRead(
                "potting.confirmation.vente",
                [
                    ['state', '=', 'active'],
                    ['date_validite', '>=', today],
                    ['date_validite', '<=', futureDate]
                ],
                ["reference", "client_id", "tonnage_disponible", "date_validite"],
                { limit: 5, order: "date_validite asc" }
            );

            // Formules en attente
            this.state.formulesPending = await this.orm.searchRead(
                "potting.formule",
                [['state', 'in', ['draft', 'validated', 'partial_paid']]],
                ["reference", "ot_id", "montant_total", "reste_a_payer", "state"],
                { limit: 5, order: "create_date desc" }
            );
        } catch (e) {
            console.log("Error loading recent data:", e);
        }
    }

    async loadProductStats() {
        try {
            const cvData = await this.orm.readGroup(
                "potting.confirmation.vente",
                [['state', 'in', ['draft', 'active']]],
                ["product_type", "tonnage_autorise:sum", "tonnage_utilise:sum"],
                ["product_type"]
            );

            this.state.productStats = cvData.map(item => ({
                product_type: item.product_type || 'Non défini',
                tonnage_autorise: item.tonnage_autorise || 0,
                tonnage_utilise: item.tonnage_utilise || 0,
                pourcentage: item.tonnage_autorise 
                    ? ((item.tonnage_utilise || 0) / item.tonnage_autorise * 100).toFixed(1) 
                    : 0
            }));
        } catch (e) {
            console.log("Error loading product stats:", e);
        }
    }

    // ========== FORMATTERS ==========
    formatNumber(value, decimals = 0) {
        if (value === null || value === undefined) return "0";
        return Number(value).toLocaleString('fr-FR', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    }

    formatCurrency(value) {
        if (value === null || value === undefined) return "0";
        return Number(value).toLocaleString('fr-FR', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        });
    }

    formatDate(dateStr) {
        if (!dateStr) return "-";
        const date = new Date(dateStr);
        return date.toLocaleDateString('fr-FR');
    }

    getProductTypeLabel(type) {
        const labels = {
            'masse': 'Masse de cacao',
            'beurre': 'Beurre de cacao',
            'poudre': 'Poudre de cacao',
            'tourteau': 'Tourteau de cacao'
        };
        return labels[type] || type;
    }

    getCvStateClass(state) {
        const classes = {
            'draft': 'bg-secondary',
            'active': 'bg-success',
            'expired': 'bg-danger',
            'consumed': 'bg-info'
        };
        return classes[state] || 'bg-secondary';
    }

    getFormuleStateClass(state) {
        const classes = {
            'draft': 'bg-secondary',
            'validated': 'bg-primary',
            'partial_paid': 'bg-warning',
            'paid': 'bg-success',
            'cancelled': 'bg-danger'
        };
        return classes[state] || 'bg-secondary';
    }

    getStateLabel(state) {
        const labels = {
            'draft': 'Brouillon',
            'active': 'Active',
            'expired': 'Expirée',
            'consumed': 'Consommée',
            'validated': 'Validée',
            'partial_paid': 'Partiellement payée',
            'paid': 'Payée',
            'cancelled': 'Annulée'
        };
        return labels[state] || state;
    }

    // ========== NAVIGATION ACTIONS ==========
    openCVList() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Confirmations de Vente",
            res_model: "potting.confirmation.vente",
            view_mode: "list,form,kanban",
            views: [[false, "list"], [false, "form"], [false, "kanban"]],
            target: "current",
        });
    }

    openFormuleList() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Formules (FO)",
            res_model: "potting.formule",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    createCV() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Nouvelle Confirmation de Vente",
            res_model: "potting.confirmation.vente",
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    createFormule() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Nouvelle Formule",
            res_model: "potting.formule",
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openCV(cvId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "potting.confirmation.vente",
            res_id: cvId,
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openFormule(formuleId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "potting.formule",
            res_id: formuleId,
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openExpiringCVs() {
        const thirtyDaysFromNow = new Date();
        thirtyDaysFromNow.setDate(thirtyDaysFromNow.getDate() + 30);
        const today = new Date().toISOString().split('T')[0];
        const futureDate = thirtyDaysFromNow.toISOString().split('T')[0];

        this.action.doAction({
            type: "ir.actions.act_window",
            name: "CV expirant bientôt",
            res_model: "potting.confirmation.vente",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [
                ['state', '=', 'active'],
                ['date_validite', '>=', today],
                ['date_validite', '<=', futureDate]
            ],
            target: "current",
        });
    }

    openPendingFormules() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Formules en attente de paiement",
            res_model: "potting.formule",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', 'in', ['draft', 'validated', 'partial_paid']]],
            target: "current",
        });
    }

    openCVsByState(state) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: `CV - ${this.getStateLabel(state)}`,
            res_model: "potting.confirmation.vente",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', '=', state]],
            target: "current",
        });
    }

    openFormulesByState(state) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: `Formules - ${this.getStateLabel(state)}`,
            res_model: "potting.formule",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', '=', state]],
            target: "current",
        });
    }
}

registry.category("actions").add("potting_cv_formule_manager_dashboard", PottingCvFormuleManagerDashboard);
