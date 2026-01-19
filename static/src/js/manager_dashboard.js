/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Dashboard pour le profil Responsable (Manager)
 * Vue globale et complète de toutes les opérations d'exportation
 */
export class PottingManagerDashboard extends Component {
    static template = "potting_management.ManagerDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            // Campagne active
            currentCampaign: null,
            
            // KPIs globaux
            globalKPIs: {
                total_contracts: 0,
                total_ot: 0,
                total_tonnage_contracted: 0,
                total_tonnage_shipped: 0,
                shipping_rate: 0,
            },
            
            // Contrats par état
            contractStats: {
                draft: 0,
                confirmed: 0,
                in_progress: 0,
                done: 0,
            },
            
            // OT par état
            otStats: {
                draft: 0,
                lots_generated: 0,
                in_progress: 0,
                ready_validation: 0,
                done: 0,
            },
            
            // Lots par état
            lotStats: {
                draft: 0,
                in_production: 0,
                ready: 0,
                potted: 0,
            },
            
            // CV stats
            cvStats: {
                total: 0,
                active: 0,
                expired: 0,
                expiring_soon: 0,
            },
            
            // Finances
            financeStats: {
                contract_value: 0,
                contract_value_xof: 0,
                invoices_pending: 0,
                invoices_paid: 0,
                formules_pending: 0,
                formules_paid: 0,
            },
            
            // Alertes
            alerts: {
                cv_expiring: 0,
                invoices_to_validate: 0,
                ot_to_validate: 0,
                formules_unpaid: 0,
            },
            
            // Top clients
            topCustomers: [],
            
            // Évolution mensuelle
            monthlyStats: [],
            
            // Activités récentes
            recentActivities: [],
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        await this.loadCampaign();
        await this.loadGlobalKPIs();
        await this.loadContractStats();
        await this.loadOTStats();
        await this.loadLotStats();
        await this.loadCVStats();
        await this.loadFinanceStats();
        await this.loadAlerts();
        await this.loadTopCustomers();
        await this.loadRecentActivities();
    }

    async loadCampaign() {
        try {
            const campaigns = await this.orm.searchRead(
                "potting.campaign",
                [['state', '=', 'active']],
                ["name", "code", "date_start", "date_end", "export_duty_rate",
                 "transit_order_count", "total_tonnage"],
                { limit: 1 }
            );
            if (campaigns.length > 0) {
                this.state.currentCampaign = campaigns[0];
            }
        } catch (e) {
            console.log("Campaign model not available");
        }
    }

    async loadGlobalKPIs() {
        try {
            // Contrats
            this.state.globalKPIs.total_contracts = await this.orm.searchCount(
                "potting.customer.order",
                [['state', 'not in', ['cancelled']]]
            );

            // OT
            this.state.globalKPIs.total_ot = await this.orm.searchCount(
                "potting.transit.order",
                [['state', 'not in', ['cancelled']]]
            );

            // Tonnages
            const contracts = await this.orm.searchRead(
                "potting.customer.order",
                [['state', 'not in', ['cancelled']]],
                ["contract_tonnage", "total_tonnage"]
            );
            
            this.state.globalKPIs.total_tonnage_contracted = contracts.reduce(
                (sum, c) => sum + (c.contract_tonnage || 0), 0
            );
            this.state.globalKPIs.total_tonnage_shipped = contracts.reduce(
                (sum, c) => sum + (c.total_tonnage || 0), 0
            );
            
            if (this.state.globalKPIs.total_tonnage_contracted > 0) {
                this.state.globalKPIs.shipping_rate = 
                    (this.state.globalKPIs.total_tonnage_shipped / this.state.globalKPIs.total_tonnage_contracted * 100);
            }
        } catch (e) {
            console.log("Error loading global KPIs:", e);
        }
    }

    async loadContractStats() {
        try {
            const states = ['draft', 'confirmed', 'in_progress', 'done'];
            for (const state of states) {
                this.state.contractStats[state] = await this.orm.searchCount(
                    "potting.customer.order",
                    [['state', '=', state]]
                );
            }
        } catch (e) {
            console.log("Error loading contract stats:", e);
        }
    }

    async loadOTStats() {
        try {
            const states = ['draft', 'lots_generated', 'in_progress', 'ready_validation', 'done'];
            for (const state of states) {
                this.state.otStats[state] = await this.orm.searchCount(
                    "potting.transit.order",
                    [['state', '=', state]]
                );
            }
        } catch (e) {
            console.log("Error loading OT stats:", e);
        }
    }

    async loadLotStats() {
        try {
            const states = ['draft', 'in_production', 'ready', 'potted'];
            for (const state of states) {
                this.state.lotStats[state] = await this.orm.searchCount(
                    "potting.lot",
                    [['state', '=', state]]
                );
            }
        } catch (e) {
            console.log("Error loading lot stats:", e);
        }
    }

    async loadCVStats() {
        try {
            this.state.cvStats.total = await this.orm.searchCount(
                "potting.confirmation.vente", []
            );
            this.state.cvStats.active = await this.orm.searchCount(
                "potting.confirmation.vente",
                [['state', '=', 'active']]
            );
            this.state.cvStats.expired = await this.orm.searchCount(
                "potting.confirmation.vente",
                [['state', '=', 'expired']]
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

    async loadFinanceStats() {
        try {
            // Valeur des contrats
            const contracts = await this.orm.searchRead(
                "potting.customer.order",
                [['state', 'not in', ['cancelled']]],
                ["total_contract_amount", "total_contract_amount_company_currency"]
            );
            
            this.state.financeStats.contract_value = contracts.reduce(
                (sum, c) => sum + (c.total_contract_amount || 0), 0
            );
            this.state.financeStats.contract_value_xof = contracts.reduce(
                (sum, c) => sum + (c.total_contract_amount_company_currency || 0), 0
            );

            // Factures transitaires
            const invoices = await this.orm.searchRead(
                "potting.forwarding.agent.invoice",
                [],
                ["amount_total", "state"]
            );
            
            this.state.financeStats.invoices_pending = invoices
                .filter(i => ['draft', 'submitted', 'validated', 'ready_payment'].includes(i.state))
                .reduce((sum, i) => sum + (i.amount_total || 0), 0);
            this.state.financeStats.invoices_paid = invoices
                .filter(i => i.state === 'paid')
                .reduce((sum, i) => sum + (i.amount_total || 0), 0);

            // Formules
            const formules = await this.orm.searchRead(
                "potting.formule",
                [],
                ["montant_total", "montant_paye", "reste_a_payer", "state"]
            );
            
            this.state.financeStats.formules_pending = formules
                .filter(f => f.state !== 'paid')
                .reduce((sum, f) => sum + (f.reste_a_payer || 0), 0);
            this.state.financeStats.formules_paid = formules.reduce(
                (sum, f) => sum + (f.montant_paye || 0), 0
            );
        } catch (e) {
            console.log("Error loading finance stats:", e);
        }
    }

    async loadAlerts() {
        try {
            // CV expirant
            const thirtyDaysFromNow = new Date();
            thirtyDaysFromNow.setDate(thirtyDaysFromNow.getDate() + 30);
            const today = new Date().toISOString().split('T')[0];
            const futureDate = thirtyDaysFromNow.toISOString().split('T')[0];
            
            this.state.alerts.cv_expiring = await this.orm.searchCount(
                "potting.confirmation.vente",
                [
                    ['state', '=', 'active'],
                    ['date_validite', '>=', today],
                    ['date_validite', '<=', futureDate]
                ]
            );

            // Factures à valider
            this.state.alerts.invoices_to_validate = await this.orm.searchCount(
                "potting.forwarding.agent.invoice",
                [['state', '=', 'submitted']]
            );

            // OT à valider
            this.state.alerts.ot_to_validate = await this.orm.searchCount(
                "potting.transit.order",
                [['state', '=', 'ready_validation']]
            );

            // Formules impayées
            this.state.alerts.formules_unpaid = await this.orm.searchCount(
                "potting.formule",
                [['state', 'in', ['draft', 'validated', 'partial_paid']]]
            );
        } catch (e) {
            console.log("Error loading alerts:", e);
        }
    }

    async loadTopCustomers() {
        try {
            const data = await this.orm.readGroup(
                "potting.customer.order",
                [['state', 'not in', ['cancelled']]],
                ["customer_id", "contract_tonnage:sum"],
                ["customer_id"],
                { orderby: "contract_tonnage desc", limit: 5 }
            );

            this.state.topCustomers = data.map(item => ({
                customer: item.customer_id ? item.customer_id[1] : 'Non défini',
                customer_id: item.customer_id ? item.customer_id[0] : null,
                tonnage: item.contract_tonnage || 0
            }));
        } catch (e) {
            console.log("Error loading top customers:", e);
        }
    }

    async loadRecentActivities() {
        try {
            // OT récents
            const recentOT = await this.orm.searchRead(
                "potting.transit.order",
                [],
                ["reference", "state", "create_date", "total_tonnage"],
                { limit: 3, order: "create_date desc" }
            );

            // Contrats récents
            const recentContracts = await this.orm.searchRead(
                "potting.customer.order",
                [],
                ["reference", "state", "create_date", "contract_tonnage"],
                { limit: 3, order: "create_date desc" }
            );

            this.state.recentActivities = [
                ...recentOT.map(ot => ({
                    type: 'ot',
                    reference: ot.reference,
                    state: ot.state,
                    date: ot.create_date,
                    value: ot.total_tonnage,
                    icon: 'fa-truck',
                    color: 'primary'
                })),
                ...recentContracts.map(c => ({
                    type: 'contract',
                    reference: c.reference,
                    state: c.state,
                    date: c.create_date,
                    value: c.contract_tonnage,
                    icon: 'fa-file-text',
                    color: 'success'
                }))
            ].sort((a, b) => new Date(b.date) - new Date(a.date)).slice(0, 5);
        } catch (e) {
            console.log("Error loading recent activities:", e);
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

    formatDateTime(dateStr) {
        if (!dateStr) return "-";
        const date = new Date(dateStr);
        return date.toLocaleDateString('fr-FR') + ' ' + date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    }

    getStateLabel(state) {
        const labels = {
            'draft': 'Brouillon',
            'confirmed': 'Confirmé',
            'in_progress': 'En cours',
            'done': 'Terminé',
            'cancelled': 'Annulé',
            'lots_generated': 'Lots générés',
            'ready_validation': 'À valider',
            'ready': 'Prêt',
            'potted': 'Empoté',
            'in_production': 'En production'
        };
        return labels[state] || state;
    }

    getStateClass(state) {
        const classes = {
            'draft': 'bg-secondary',
            'confirmed': 'bg-primary',
            'in_progress': 'bg-info',
            'done': 'bg-success',
            'cancelled': 'bg-danger',
            'lots_generated': 'bg-info',
            'ready_validation': 'bg-warning',
            'ready': 'bg-primary',
            'potted': 'bg-success',
            'in_production': 'bg-warning'
        };
        return classes[state] || 'bg-secondary';
    }

    // ========== NAVIGATION ==========
    openContracts() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Contrats clients",
            res_model: "potting.customer.order",
            view_mode: "list,form,kanban",
            views: [[false, "list"], [false, "form"], [false, "kanban"]],
            target: "current",
        });
    }

    openTransitOrders() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Ordres de Transit",
            res_model: "potting.transit.order",
            view_mode: "list,form,kanban",
            views: [[false, "list"], [false, "form"], [false, "kanban"]],
            target: "current",
        });
    }

    openLots() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Lots",
            res_model: "potting.lot",
            view_mode: "list,form,kanban",
            views: [[false, "list"], [false, "form"], [false, "kanban"]],
            target: "current",
        });
    }

    openCVs() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Confirmations de Vente",
            res_model: "potting.confirmation.vente",
            view_mode: "list,form,kanban",
            views: [[false, "list"], [false, "form"], [false, "kanban"]],
            target: "current",
        });
    }

    openFormules() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Formules (FO)",
            res_model: "potting.formule",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openInvoices() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Factures transitaires",
            res_model: "potting.forwarding.agent.invoice",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openOTToValidate() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "OT à valider",
            res_model: "potting.transit.order",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', '=', 'ready_validation']],
            target: "current",
        });
    }

    openInvoicesToValidate() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Factures à valider",
            res_model: "potting.forwarding.agent.invoice",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', '=', 'submitted']],
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

    openUnpaidFormules() {
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

    openContractsByState(state) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: `Contrats - ${this.getStateLabel(state)}`,
            res_model: "potting.customer.order",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', '=', state]],
            target: "current",
        });
    }

    openOTByState(state) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: `OT - ${this.getStateLabel(state)}`,
            res_model: "potting.transit.order",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', '=', state]],
            target: "current",
        });
    }

    openLotsByState(state) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: `Lots - ${this.getStateLabel(state)}`,
            res_model: "potting.lot",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', '=', state]],
            target: "current",
        });
    }

    openCustomerContracts(customerId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Contrats du client",
            res_model: "potting.customer.order",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['customer_id', '=', customerId]],
            target: "current",
        });
    }

    openSettings() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Paramètres",
            res_model: "res.config.settings",
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
            context: { module: 'potting_management' }
        });
    }

    openCampaigns() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Campagnes",
            res_model: "potting.campaign",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("potting_manager_dashboard", PottingManagerDashboard);
