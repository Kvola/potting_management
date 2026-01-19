/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class PottingCVFormuleDashboard extends Component {
    static template = "potting_management.CVFormuleDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            // Current campaign
            currentCampaign: null,
            // Company currency
            companyCurrency: null,
            // CV statistics
            cvStats: {
                total: 0,
                active: 0,
                expired: 0,
                consumed: 0,
                tonnage_autorise: 0,
                tonnage_utilise: 0,
                tonnage_restant: 0,
                expiring_soon: 0,
                montant_total: 0,
            },
            // Formule statistics
            formuleStats: {
                total: 0,
                draft: 0,
                validated: 0,
                partial_paid: 0,
                paid: 0,
                montant_total: 0,
                montant_paye: 0,
                montant_restant: 0,
            },
            // Recent CVs
            recentCVs: [],
            // Recent Formules
            recentFormules: [],
            // CVs by month (for chart)
            cvByMonth: [],
            // Formules by month (for chart)
            formuleByMonth: [],
            // Loading state
            isLoading: true,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        try {
            // Load current campaign
            await this.loadCurrentCampaign();
            
            // Load company currency
            await this.loadCompanyCurrency();
            
            // Load CV statistics
            await this.loadCVStats();
            
            // Load Formule statistics
            await this.loadFormuleStats();
            
            // Load recent CVs
            await this.loadRecentCVs();
            
            // Load recent Formules
            await this.loadRecentFormules();
            
        } catch (e) {
            console.error("Error loading dashboard data:", e);
        } finally {
            this.state.isLoading = false;
        }
    }

    async loadCurrentCampaign() {
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
    }

    async loadCompanyCurrency() {
        try {
            const companies = await this.orm.searchRead(
                "res.company",
                [['id', '=', 1]],
                ["currency_id"],
                { limit: 1 }
            );
            if (companies.length > 0 && companies[0].currency_id) {
                const currencies = await this.orm.searchRead(
                    "res.currency",
                    [['id', '=', companies[0].currency_id[0]]],
                    ["symbol", "name"],
                    { limit: 1 }
                );
                if (currencies.length > 0) {
                    this.state.companyCurrency = currencies[0];
                }
            }
        } catch (e) {
            console.log("Could not load company currency");
        }
    }

    async loadCVStats() {
        // Count by state
        const states = ['active', 'expired', 'consumed'];
        for (const state of states) {
            const count = await this.orm.searchCount("potting.confirmation.vente", [['state', '=', state]]);
            this.state.cvStats[state] = count;
        }
        
        // Total
        this.state.cvStats.total = await this.orm.searchCount("potting.confirmation.vente", []);
        
        // CVs expiring soon (within 30 days)
        const today = new Date();
        const thirtyDaysLater = new Date(today);
        thirtyDaysLater.setDate(thirtyDaysLater.getDate() + 30);
        const expiringCount = await this.orm.searchCount("potting.confirmation.vente", [
            ['state', '=', 'active'],
            ['date_end', '<=', thirtyDaysLater.toISOString().split('T')[0]],
            ['date_end', '>=', today.toISOString().split('T')[0]]
        ]);
        this.state.cvStats.expiring_soon = expiringCount;
        
        // Tonnage statistics
        const allCVs = await this.orm.searchRead(
            "potting.confirmation.vente",
            [['state', 'in', ['active', 'consumed']]],
            ["tonnage_autorise", "tonnage_utilise", "tonnage_restant", "prix_tonnage"]
        );
        
        this.state.cvStats.tonnage_autorise = allCVs.reduce(
            (sum, cv) => sum + (cv.tonnage_autorise || 0), 0
        );
        this.state.cvStats.tonnage_utilise = allCVs.reduce(
            (sum, cv) => sum + (cv.tonnage_utilise || 0), 0
        );
        this.state.cvStats.tonnage_restant = allCVs.reduce(
            (sum, cv) => sum + (cv.tonnage_restant || 0), 0
        );
        
        // Montant total (tonnage * prix)
        this.state.cvStats.montant_total = allCVs.reduce(
            (sum, cv) => sum + ((cv.tonnage_autorise || 0) * (cv.prix_tonnage || 0)), 0
        );
    }

    async loadFormuleStats() {
        // Count by state
        const states = ['draft', 'validated', 'partial_paid', 'paid'];
        for (const state of states) {
            const count = await this.orm.searchCount("potting.formule", [['state', '=', state]]);
            this.state.formuleStats[state] = count;
        }
        
        // Total
        this.state.formuleStats.total = await this.orm.searchCount("potting.formule", []);
        
        // Financial statistics
        const allFormules = await this.orm.searchRead(
            "potting.formule",
            [],
            ["montant_total", "montant_paye", "montant_restant"]
        );
        
        this.state.formuleStats.montant_total = allFormules.reduce(
            (sum, f) => sum + (f.montant_total || 0), 0
        );
        this.state.formuleStats.montant_paye = allFormules.reduce(
            (sum, f) => sum + (f.montant_paye || 0), 0
        );
        this.state.formuleStats.montant_restant = allFormules.reduce(
            (sum, f) => sum + (f.montant_restant || 0), 0
        );
    }

    async loadRecentCVs() {
        this.state.recentCVs = await this.orm.searchRead(
            "potting.confirmation.vente",
            [],
            ["name", "reference_ccc", "date_emission", "date_end", "tonnage_autorise", 
             "tonnage_utilise", "tonnage_restant", "state", "prix_tonnage", "is_expired"],
            { limit: 10, order: "create_date desc" }
        );
    }

    async loadRecentFormules() {
        this.state.recentFormules = await this.orm.searchRead(
            "potting.formule",
            [],
            ["name", "reference_ccc", "numero_fo1", "date_emission", "tonnage", 
             "montant_total", "montant_paye", "montant_restant", "state", 
             "confirmation_vente_id", "transit_order_id"],
            { limit: 10, order: "create_date desc" }
        );
    }

    // =========================================================================
    // ACTION METHODS
    // =========================================================================

    createCV() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Nouvelle Confirmation de Vente',
            res_model: 'potting.confirmation.vente',
            views: [[false, 'form']],
            target: 'current',
        });
    }

    createFormule() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Nouvelle Formule',
            res_model: 'potting.formule',
            views: [[false, 'form']],
            target: 'current',
        });
    }

    openCVs(state) {
        const domain = state ? [['state', '=', state]] : [];
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Confirmations de Vente',
            res_model: 'potting.confirmation.vente',
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            domain: domain,
            context: {},
        });
    }

    openExpiringCVs() {
        const today = new Date();
        const thirtyDaysLater = new Date(today);
        thirtyDaysLater.setDate(thirtyDaysLater.getDate() + 30);
        
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'CV expirantes bientôt',
            res_model: 'potting.confirmation.vente',
            views: [[false, 'list'], [false, 'form']],
            domain: [
                ['state', '=', 'active'],
                ['date_end', '<=', thirtyDaysLater.toISOString().split('T')[0]],
                ['date_end', '>=', today.toISOString().split('T')[0]]
            ],
            context: {},
        });
    }

    openFormules(state) {
        const domain = state ? [['state', '=', state]] : [];
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Formules',
            res_model: 'potting.formule',
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            domain: domain,
            context: {},
        });
    }

    openCV(cvId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Confirmation de Vente',
            res_model: 'potting.confirmation.vente',
            res_id: cvId,
            views: [[false, 'form']],
            target: 'current',
        });
    }

    openFormule(formuleId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Formule',
            res_model: 'potting.formule',
            res_id: formuleId,
            views: [[false, 'form']],
            target: 'current',
        });
    }

    openCampaigns() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Campagnes',
            res_model: 'potting.campaign',
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            domain: [],
            context: {},
        });
    }

    openTaxeTypes() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Types de Taxes CCC',
            res_model: 'potting.taxe.type',
            views: [[false, 'list'], [false, 'form']],
            domain: [],
            context: {},
        });
    }

    // =========================================================================
    // UTILITY METHODS
    // =========================================================================

    getCVStateLabel(state) {
        const labels = {
            'active': 'Active',
            'expired': 'Expirée',
            'consumed': 'Consommée',
        };
        return labels[state] || state;
    }

    getCVStateBadgeClass(state) {
        const classes = {
            'active': 'bg-success',
            'expired': 'bg-danger',
            'consumed': 'bg-info',
        };
        return classes[state] || 'bg-secondary';
    }

    getFormuleStateLabel(state) {
        const labels = {
            'draft': 'Brouillon',
            'validated': 'Validée',
            'partial_paid': 'Partiellement payée',
            'paid': 'Payée',
            'cancelled': 'Annulée',
        };
        return labels[state] || state;
    }

    getFormuleStateBadgeClass(state) {
        const classes = {
            'draft': 'bg-secondary',
            'validated': 'bg-primary',
            'partial_paid': 'bg-warning',
            'paid': 'bg-success',
            'cancelled': 'bg-danger',
        };
        return classes[state] || 'bg-secondary';
    }

    formatNumber(num, decimals = 2) {
        if (typeof num !== 'number') return '0';
        return num.toLocaleString('fr-FR', { 
            minimumFractionDigits: decimals, 
            maximumFractionDigits: decimals 
        });
    }

    formatCurrency(num) {
        if (typeof num !== 'number') return '0';
        return num.toLocaleString('fr-FR', { 
            minimumFractionDigits: 0, 
            maximumFractionDigits: 0 
        });
    }

    formatDate(dateStr) {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        return date.toLocaleDateString('fr-FR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
    }

    getTonnagePercentage() {
        const autorise = this.state.cvStats.tonnage_autorise;
        const utilise = this.state.cvStats.tonnage_utilise;
        if (autorise <= 0) return 0;
        return Math.min(100, (utilise / autorise) * 100);
    }

    getPaymentPercentage() {
        const total = this.state.formuleStats.montant_total;
        const paye = this.state.formuleStats.montant_paye;
        if (total <= 0) return 0;
        return Math.min(100, (paye / total) * 100);
    }
}

registry.category("actions").add("potting_cv_formule_dashboard", PottingCVFormuleDashboard);
