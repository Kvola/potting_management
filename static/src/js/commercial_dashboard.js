/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class PottingCommercialDashboard extends Component {
    static template = "potting_management.CommercialDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            // Current campaign
            currentCampaign: null,
            // Company currency
            companyCurrency: null,
            // Contract statistics
            contracts: {
                draft: 0,
                confirmed: 0,
                in_progress: 0,
                done: 0,
                total: 0,
            },
            // Tonnage statistics
            tonnage: {
                contract_total: 0,
                ot_total: 0,
                remaining: 0,
                percentage_used: 0,
            },
            // Amount statistics (new)
            amounts: {
                total_contract: 0,
                total_company_currency: 0,
                currency_symbol: '',
                company_currency_symbol: '',
            },
            // CV statistics (NEW)
            cvStats: {
                total: 0,
                active: 0,
                expired: 0,
                consumed: 0,
                tonnage_autorise: 0,
                tonnage_utilise: 0,
                tonnage_restant: 0,
                expiring_soon: 0,  // Expire dans 30 jours
            },
            // Formule statistics (NEW)
            formuleStats: {
                total: 0,
                draft: 0,
                validated: 0,
                partial_paid: 0,
                paid: 0,
                total_montant: 0,
                total_paye: 0,
                awaiting_payment: 0,
            },
            // Product type statistics
            productStats: [],
            // Recent contracts
            recentContracts: [],
            // Contracts by customer
            customerStats: [],
            // Monthly evolution
            monthlyContracts: [],
            // Recent CV (NEW)
            recentCVs: [],
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        // Load current campaign
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

        // Load contract counts by state
        const orderStates = ['draft', 'confirmed', 'in_progress', 'done'];
        for (const state of orderStates) {
            const count = await this.orm.searchCount("potting.customer.order", [['state', '=', state]]);
            this.state.contracts[state] = count;
        }
        this.state.contracts.total = orderStates.reduce(
            (sum, state) => sum + this.state.contracts[state], 0
        );

        // Load company currency
        try {
            const companies = await this.orm.searchRead(
                "res.company",
                [['id', '=', 1]],  // Current company
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
                    this.state.amounts.company_currency_symbol = currencies[0].symbol;
                }
            }
        } catch (e) {
            console.log("Could not load company currency");
        }

        // Load tonnage statistics
        const allContracts = await this.orm.searchRead(
            "potting.customer.order",
            [['state', 'not in', ['cancelled']]],
            ["contract_tonnage", "total_tonnage", "remaining_contract_tonnage"]
        );
        
        this.state.tonnage.contract_total = allContracts.reduce(
            (sum, c) => sum + (c.contract_tonnage || 0), 0
        );
        this.state.tonnage.ot_total = allContracts.reduce(
            (sum, c) => sum + (c.total_tonnage || 0), 0
        );
        this.state.tonnage.remaining = this.state.tonnage.contract_total - this.state.tonnage.ot_total;
        this.state.tonnage.percentage_used = this.state.tonnage.contract_total > 0 
            ? (this.state.tonnage.ot_total / this.state.tonnage.contract_total) * 100 
            : 0;

        // Load amount statistics
        const contractsWithAmounts = await this.orm.searchRead(
            "potting.customer.order",
            [['state', 'not in', ['cancelled']]],
            ["total_amount", "total_amount_company_currency", "currency_id", "company_currency_id"]
        );
        
        this.state.amounts.total_contract = contractsWithAmounts.reduce(
            (sum, c) => sum + (c.total_amount || 0), 0
        );
        this.state.amounts.total_company_currency = contractsWithAmounts.reduce(
            (sum, c) => sum + (c.total_amount_company_currency || 0), 0
        );
        
        // Get currency symbols from first contract
        if (contractsWithAmounts.length > 0 && contractsWithAmounts[0].currency_id) {
            try {
                const currency = await this.orm.searchRead(
                    "res.currency",
                    [['id', '=', contractsWithAmounts[0].currency_id[0]]],
                    ["symbol"],
                    { limit: 1 }
                );
                if (currency.length > 0) {
                    this.state.amounts.currency_symbol = currency[0].symbol;
                }
            } catch (e) {
                console.log("Could not load contract currency");
            }
        }

        // Load product type statistics
        const productTypes = ['cocoa_mass', 'cocoa_butter', 'cocoa_cake', 'cocoa_powder'];
        const productLabels = {
            'cocoa_mass': 'Masse de cacao',
            'cocoa_butter': 'Beurre de cacao',
            'cocoa_cake': 'Cake de cacao',
            'cocoa_powder': 'Poudre de cacao'
        };
        
        this.state.productStats = [];
        for (const type of productTypes) {
            const contracts = await this.orm.searchRead(
                "potting.customer.order",
                [['product_type', '=', type], ['state', 'not in', ['cancelled']]],
                ["contract_tonnage", "total_tonnage", "unit_price"]
            );
            const contractTonnage = contracts.reduce((sum, c) => sum + (c.contract_tonnage || 0), 0);
            const usedTonnage = contracts.reduce((sum, c) => sum + (c.total_tonnage || 0), 0);
            const totalValue = contracts.reduce(
                (sum, c) => sum + ((c.contract_tonnage || 0) * (c.unit_price || 0)), 0
            );
            this.state.productStats.push({
                type: type,
                label: productLabels[type],
                count: contracts.length,
                contractTonnage: contractTonnage,
                usedTonnage: usedTonnage,
                remainingTonnage: contractTonnage - usedTonnage,
                totalValue: totalValue,
                percentage: contractTonnage > 0 ? (usedTonnage / contractTonnage) * 100 : 0,
            });
        }

        // Load recent contracts
        this.state.recentContracts = await this.orm.searchRead(
            "potting.customer.order",
            [['state', 'not in', ['cancelled']]],
            ["name", "customer_id", "product_type", "contract_tonnage", "total_tonnage", 
             "remaining_contract_tonnage", "unit_price", "state", "date_order"],
            { limit: 10, order: "create_date desc" }
        );

        // Load customer statistics (top 5 customers)
        const customerGroups = await this.orm.readGroup(
            "potting.customer.order",
            [['state', 'not in', ['cancelled']]],
            ["customer_id", "contract_tonnage:sum", "total_tonnage:sum"],
            ["customer_id"],
            { orderby: "contract_tonnage desc", limit: 5 }
        );
        this.state.customerStats = customerGroups.map(g => ({
            customer: g.customer_id ? g.customer_id[1] : 'Non défini',
            customerId: g.customer_id ? g.customer_id[0] : false,
            contractTonnage: g.contract_tonnage || 0,
            usedTonnage: g.total_tonnage || 0,
            percentage: g.contract_tonnage > 0 ? (g.total_tonnage / g.contract_tonnage) * 100 : 0,
        }));
        
        // ==============================================================
        // CV STATISTICS (NEW)
        // ==============================================================
        try {
            // Total CV par état
            const cvStates = ['draft', 'active', 'consumed', 'expired', 'cancelled'];
            for (const state of cvStates) {
                const count = await this.orm.searchCount("potting.confirmation.vente", [['state', '=', state]]);
                if (state === 'active') this.state.cvStats.active = count;
                else if (state === 'expired') this.state.cvStats.expired = count;
                else if (state === 'consumed') this.state.cvStats.consumed = count;
            }
            this.state.cvStats.total = await this.orm.searchCount("potting.confirmation.vente", []);
            
            // Tonnage CV
            const allCVs = await this.orm.searchRead(
                "potting.confirmation.vente",
                [['state', '=', 'active']],
                ["tonnage_autorise", "tonnage_utilise", "tonnage_restant", "date_end"]
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
            
            // CV expirant bientôt (30 jours)
            const today = new Date();
            const in30Days = new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000);
            this.state.cvStats.expiring_soon = await this.orm.searchCount(
                "potting.confirmation.vente",
                [
                    ['state', '=', 'active'],
                    ['date_end', '<=', in30Days.toISOString().split('T')[0]],
                    ['date_end', '>=', today.toISOString().split('T')[0]]
                ]
            );
            
            // CV récentes
            this.state.recentCVs = await this.orm.searchRead(
                "potting.confirmation.vente",
                [['state', 'in', ['active', 'consumed']]],
                ["name", "reference_ccc", "tonnage_autorise", "tonnage_restant", 
                 "tonnage_progress", "date_end", "state"],
                { limit: 5, order: "date_emission desc" }
            );
        } catch (e) {
            console.log("Could not load CV statistics:", e);
        }
        
        // ==============================================================
        // FORMULE STATISTICS (NEW)
        // ==============================================================
        try {
            // Total Formules par état
            const formuleStates = ['draft', 'validated', 'partial_paid', 'paid'];
            for (const state of formuleStates) {
                const count = await this.orm.searchCount("potting.formule", [['state', '=', state]]);
                this.state.formuleStats[state] = count;
            }
            this.state.formuleStats.total = await this.orm.searchCount(
                "potting.formule", 
                [['state', '!=', 'cancelled']]
            );
            
            // Montants des formules
            const allFormules = await this.orm.searchRead(
                "potting.formule",
                [['state', 'in', ['validated', 'partial_paid', 'paid']]],
                ["montant_net", "total_paye", "state"]
            );
            this.state.formuleStats.total_montant = allFormules.reduce(
                (sum, f) => sum + (f.montant_net || 0), 0
            );
            this.state.formuleStats.total_paye = allFormules.reduce(
                (sum, f) => sum + (f.total_paye || 0), 0
            );
            this.state.formuleStats.awaiting_payment = allFormules.filter(
                f => f.state === 'validated' || f.state === 'partial_paid'
            ).length;
        } catch (e) {
            console.log("Could not load Formule statistics:", e);
        }
    }

    // Navigation methods
    openContracts(state) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Contrats clients',
            res_model: 'potting.customer.order',
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            domain: state ? [['state', '=', state]] : [],
            context: {},
        });
    }

    openContractsByProduct(productType) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Contrats clients',
            res_model: 'potting.customer.order',
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            domain: [['product_type', '=', productType]],
            context: {},
        });
    }

    openContractsByCustomer(customerId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Contrats clients',
            res_model: 'potting.customer.order',
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            domain: [['customer_id', '=', customerId]],
            context: {},
        });
    }

    createContract() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Nouveau contrat',
            res_model: 'potting.customer.order',
            views: [[false, 'form']],
            target: 'current',
        });
    }

    importContracts() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Importer des contrats',
            res_model: 'potting.import.contracts.wizard',
            views: [[false, 'form']],
            target: 'new',
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

    // CV Navigation methods (NEW)
    openCVs(state) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Confirmations de Vente',
            res_model: 'potting.confirmation.vente',
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            domain: state ? [['state', '=', state]] : [],
            context: {},
        });
    }

    openCVsExpiringSoon() {
        const today = new Date();
        const in30Days = new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000);
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'CV expirant bientôt',
            res_model: 'potting.confirmation.vente',
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            domain: [
                ['state', '=', 'active'],
                ['date_end', '<=', in30Days.toISOString().split('T')[0]],
                ['date_end', '>=', today.toISOString().split('T')[0]]
            ],
            context: {},
        });
    }

    createCV() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Nouvelle Confirmation de Vente',
            res_model: 'potting.confirmation.vente',
            views: [[false, 'form']],
            target: 'current',
        });
    }

    // Formule Navigation methods (NEW)
    openFormules(state) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Formules',
            res_model: 'potting.formule',
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            domain: state ? [['state', '=', state]] : [],
            context: {},
        });
    }

    openFormulesAwaitingPayment() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Formules en attente de paiement',
            res_model: 'potting.formule',
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            domain: [['state', 'in', ['validated', 'partial_paid']]],
            context: {},
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

    // Helper methods
    getStateLabel(state) {
        const labels = {
            'draft': 'Brouillon',
            'confirmed': 'Confirmé',
            'in_progress': 'En cours',
            'done': 'Terminé',
            'cancelled': 'Annulé'
        };
        return labels[state] || state;
    }

    getStateBadgeClass(state) {
        const classes = {
            'draft': 'bg-secondary',
            'confirmed': 'bg-info',
            'in_progress': 'bg-warning',
            'done': 'bg-success',
            'cancelled': 'bg-danger'
        };
        return classes[state] || 'bg-secondary';
    }

    getProductTypeLabel(type) {
        const labels = {
            'cocoa_mass': 'Masse',
            'cocoa_butter': 'Beurre',
            'cocoa_cake': 'Cake',
            'cocoa_powder': 'Poudre'
        };
        return labels[type] || type;
    }

    getProductTypeIcon(type) {
        const icons = {
            'cocoa_mass': 'fa-circle',
            'cocoa_butter': 'fa-tint',
            'cocoa_cake': 'fa-stop',
            'cocoa_powder': 'fa-cloud'
        };
        return icons[type] || 'fa-cube';
    }

    formatNumber(num, decimals = 2) {
        if (typeof num !== 'number') return '0.00';
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
}

registry.category("actions").add("potting_commercial_dashboard", PottingCommercialDashboard);
